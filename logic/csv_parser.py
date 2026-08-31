"""Safe CSV parsing for Shopify orders and Stripe payout exports."""

import io
import re

import pandas as pd


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _pick_column(columns: list[str], candidates: list[str]) -> str | None:
    for name in candidates:
        if name in columns:
            return name
    for col in columns:
        for name in candidates:
            if name in col:
                return col
    return None


def _clean_money(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(r"[$,\s]", "", regex=True)
        .str.replace(r"\((.*)\)", r"-\1", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _extract_order_id(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    match = re.search(r"#?(\d{3,})", text)
    if match:
        return match.group(1)
    return re.sub(r"[^a-zA-Z0-9\-]", "", text) or None


def parse_shopify_csv(source: bytes | str) -> pd.DataFrame:
    """Parse Shopify orders export into order_id + gross_sales."""
    try:
        df = pd.read_csv(io.BytesIO(source) if isinstance(source, bytes) else io.StringIO(source))
    except Exception as exc:
        raise ValueError(f"Could not read Shopify CSV: {exc}") from exc

    if df.empty:
        raise ValueError("Shopify CSV is empty.")

    df = _normalize_columns(df)
    id_col = _pick_column(
        list(df.columns),
        ["name", "order id", "order_id", "order number", "order name", "id"],
    )
    gross_col = _pick_column(
        list(df.columns),
        ["total", "gross sales", "gross", "order total", "amount", "total sales"],
    )
    if not id_col or not gross_col:
        raise ValueError("Shopify CSV must include order ID and total/gross columns.")

    out = pd.DataFrame(
        {
            "order_id": df[id_col].map(_extract_order_id),
            "gross_sales": _clean_money(df[gross_col]),
        }
    )
    return out.dropna(subset=["order_id", "gross_sales"]).reset_index(drop=True)


def parse_stripe_csv(source: bytes | str) -> pd.DataFrame:
    """Parse Stripe balance/payout export into order_id + fee + net."""
    try:
        df = pd.read_csv(io.BytesIO(source) if isinstance(source, bytes) else io.StringIO(source))
    except Exception as exc:
        raise ValueError(f"Could not read Stripe CSV: {exc}") from exc

    if df.empty:
        raise ValueError("Stripe CSV is empty.")

    df = _normalize_columns(df)
    id_col = _pick_column(
        list(df.columns),
        ["order id", "order_id", "shopify order", "description", "source", "metadata"],
    )
    gross_col = _pick_column(list(df.columns), ["gross", "amount", "charge amount", "total"])
    fee_col = _pick_column(list(df.columns), ["fee", "fees", "stripe fee", "processing fee"])
    net_col = _pick_column(list(df.columns), ["net", "net amount", "payout", "deposit"])

    if not id_col:
        raise ValueError("Stripe CSV must include an order reference or description column.")

    out = pd.DataFrame({"order_id": df[id_col].map(_extract_order_id)})
    out["gross_sales"] = _clean_money(df[gross_col]) if gross_col else pd.NA
    out["processing_fee"] = _clean_money(df[fee_col]) if fee_col else pd.NA
    out["net_payout"] = _clean_money(df[net_col]) if net_col else pd.NA
    return out.dropna(subset=["order_id"]).reset_index(drop=True)
