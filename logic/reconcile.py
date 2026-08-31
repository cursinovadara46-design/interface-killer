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


def reconcile_orders(shopify_df: pd.DataFrame, stripe_df: pd.DataFrame):
    shopify = shopify_df.copy()
    stripe = stripe_df.copy()

    shopify["order_id_clean"] = shopify["Name"].astype(str).str.strip()
    stripe["description_clean"] = stripe["Description"].astype(str).str.strip()

    merged = pd.merge(
        shopify,
        stripe,
        left_on="order_id_clean",
        right_on="description_clean",
        how="outer",
        suffixes=("_shopify", "_stripe"),
    )

    reconciled_rows = []
    matched_count = 0
    mismatch_count = 0
    missing_stripe_count = 0
    missing_shopify_count = 0

    for idx, row in merged.iterrows():
        order_id = (
            row["order_id_clean"]
            if pd.notna(row["order_id_clean"])
            else row["description_clean"]
        )
        has_shopify = pd.notna(row.get("Total_shopify")) or pd.notna(row.get("Name"))
        has_stripe = pd.notna(row.get("Amount")) or pd.notna(row.get("Description"))

        if has_shopify and has_stripe:
            gross = float(row.get("Total_shopify", 0.0) or 0.0)
            expected_fee = round((gross * STRIPE_RATE) + STRIPE_FIXED_FEE, 2)
            expected_net = round(gross - expected_fee, 2)

            actual_fee = abs(float(row.get("Fee", 0.0) or 0.0))
            actual_net = float(row.get("Net", 0.0) or 0.0)

            fee_diff = abs(expected_fee - actual_fee)
            net_diff = abs(expected_net - actual_net)

            if fee_diff <= 0.05 and net_diff <= 0.05:
                status = "Matched"
                matched_count += 1
            else:
                status = "Fee Mismatch"
                mismatch_count += 1

            reconciled_rows.append(
                {
                    "Shopify Order ID": order_id,
                    "Gross Sales ($)": gross,
                    "Processing Fee ($)": actual_fee,
                    "Net Payout ($)": actual_net,
                    "Reconciliation Status": status,
                }
            )
        elif has_shopify and not has_stripe:
            gross = float(row.get("Total_shopify", 0.0) or 0.0)
            missing_stripe_count += 1
            reconciled_rows.append(
                {
                    "Shopify Order ID": order_id,
                    "Gross Sales ($)": gross,
                    "Processing Fee ($)": 0.0,
                    "Net Payout ($)": 0.0,
                    "Reconciliation Status": "Missing in Stripe",
                }
            )
        elif has_stripe and not has_shopify:
            missing_shopify_count += 1
            reconciled_rows.append(
                {
                    "Shopify Order ID": order_id,
                    "Gross Sales ($)": 0.0,
                    "Processing Fee ($)": abs(float(row.get("Fee", 0.0) or 0.0)),
                    "Net Payout ($)": float(row.get("Net", 0.0) or 0.0),
                    "Reconciliation Status": "Missing in Shopify",
                }
            )

    summary = pd.DataFrame(reconciled_rows)

    metrics = {
        "total_orders": len(summary),
        "matched": matched_count,
        "mismatched": mismatch_count,
        "missing_stripe": missing_stripe_count,
        "missing_shopify": missing_shopify_count,
    }

    return summary, metrics


def _format_csv_amount(value) -> str:
    try:
        return f"{float(value):.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return str(value)


def summary_to_csv(summary: pd.DataFrame) -> bytes:
    export = summary.copy()
    money_cols = (
        "Gross Sales ($)",
        "Processing Fee ($)",
        "Net Payout ($)",
        "Gross Sales",
        "Processing Fee",
        "Net Payout",
    )
    for col in money_cols:
        if col in export.columns:
            export[col] = export[col].apply(_format_csv_amount)

    buf = BytesIO()
    export.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
    return buf.getvalue()