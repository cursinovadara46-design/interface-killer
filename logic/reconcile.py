"""Reconcile Shopify orders against Stripe payout rows."""

from io import BytesIO

import pandas as pd

STRIPE_RATE = 0.029
STRIPE_FIXED_FEE = 0.30
SUMMARY_COLUMNS = [
    "Shopify Order ID",
    "Gross Sales ($)",
    "Processing Fee ($)",
    "Net Payout ($)",
    "Reconciliation Status",
]


def _estimate_fee(gross: float) -> float:
    return round(gross * STRIPE_RATE + STRIPE_FIXED_FEE, 2)


def _status(
    shopify_gross: float | None,
    stripe_gross: float | None,
    has_shopify: bool,
    has_stripe: bool,
) -> str:
    if has_shopify and not has_stripe:
        return "Shopify Only — no Stripe match"
    if has_stripe and not has_shopify:
        return "Stripe Only — no Shopify match"
    if stripe_gross is None or pd.isna(stripe_gross):
        return "Matched — Stripe fee estimated"
    if shopify_gross is not None and abs(shopify_gross - stripe_gross) <= 0.05:
        return "Matched"
    return "Amount Mismatch — review manually"


def reconcile_orders(shopify_df: pd.DataFrame, stripe_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    shopify = shopify_df.groupby("order_id", as_index=False)["gross_sales"].sum()
    stripe = stripe_df.groupby("order_id", as_index=False).agg(
        gross_sales=("gross_sales", "sum"),
        processing_fee=("processing_fee", "sum"),
        net_payout=("net_payout", "sum"),
    )
    merged = shopify.merge(stripe, on="order_id", how="outer", suffixes=("_shopify", "_stripe"))

    rows = []
    for _, row in merged.iterrows():
        order_id = row["order_id"]
        gross = float(row["gross_sales_shopify"]) if pd.notna(row["gross_sales_shopify"]) else float(
            row["gross_sales_stripe"] or 0
        )
        has_shopify = pd.notna(row["gross_sales_shopify"])
        has_stripe = pd.notna(row["gross_sales_stripe"]) or pd.notna(row["processing_fee"]) or pd.notna(
            row["net_payout"]
        )
        stripe_gross = row["gross_sales_stripe"] if pd.notna(row["gross_sales_stripe"]) else None
        shopify_gross = float(row["gross_sales_shopify"]) if has_shopify else None

        if pd.notna(row["processing_fee"]) and row["processing_fee"] > 0:
            fee = float(row["processing_fee"])
        else:
            fee = _estimate_fee(gross)

        if pd.notna(row["net_payout"]) and row["net_payout"] > 0:
            net = float(row["net_payout"])
        else:
            net = round(gross - fee, 2)

        rows.append(
            {
                "Shopify Order ID": f"#{order_id}",
                "Gross Sales ($)": round(gross, 2),
                "Processing Fee ($)": round(fee, 2),
                "Net Payout ($)": round(net, 2),
                "Reconciliation Status": _status(
                    shopify_gross,
                    stripe_gross,
                    has_shopify,
                    has_stripe,
                ),
            }
        )

    summary = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    metrics = {
        "total_gross": round(summary["Gross Sales ($)"].sum(), 2),
        "total_fees": round(summary["Processing Fee ($)"].sum(), 2),
        "net_deposit": round(summary["Net Payout ($)"].sum(), 2),
    }
    return summary, metrics


def summary_to_csv(summary: pd.DataFrame, sep: str = ",") -> bytes:
    export = summary.copy()
    money_cols = ("Gross Sales ($)", "Processing Fee ($)", "Net Payout ($)")
    for col in money_cols:
        export[col] = export[col].map(lambda x: f"{float(str(x).replace('$', '')):.2f}")
    buf = BytesIO()
    export.to_csv(buf, index=False, sep=sep, encoding="utf-8-sig")
    return buf.getvalue()
