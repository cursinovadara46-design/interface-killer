"""Shopify & Stripe Payout Reconciler — Streamlit UI only."""

import streamlit as st

from logic.csv_parser import parse_shopify_csv, parse_stripe_csv
from logic.demo_data import get_demo_shopify_csv, get_demo_stripe_csv
from logic.reconcile import reconcile_orders, summary_to_csv

st.set_page_config(
    page_title="Shopify & Stripe Payout Reconciler",
    page_icon="💵",
    layout="wide",
)

st.title("💵 1-Click Shopify & Stripe Payout Reconciler")
st.subheader(
    "Match Shopify orders with Stripe payouts in minutes — built for US e-commerce "
    "store owners and bookkeepers preparing QuickBooks-ready deposit summaries."
)

if "shopify_bytes" not in st.session_state:
    st.session_state.shopify_bytes = None
if "stripe_bytes" not in st.session_state:
    st.session_state.stripe_bytes = None

demo_col, _ = st.columns([1, 3])
with demo_col:
    if st.button("⚡ Load Sample Data", type="primary"):
        st.session_state.shopify_bytes = get_demo_shopify_csv()
        st.session_state.stripe_bytes = get_demo_stripe_csv()
        st.rerun()

st.divider()

upload_col1, upload_col2 = st.columns(2)
with upload_col1:
    shopify_file = st.file_uploader("Shopify Orders CSV", type=["csv"], key="shopify_upload")
with upload_col2:
    stripe_file = st.file_uploader("Stripe Balance/Payout CSV", type=["csv"], key="stripe_upload")

if shopify_file is not None:
    st.session_state.shopify_bytes = shopify_file.getvalue()
if stripe_file is not None:
    st.session_state.stripe_bytes = stripe_file.getvalue()

shopify_bytes = st.session_state.shopify_bytes
stripe_bytes = st.session_state.stripe_bytes

if shopify_bytes and stripe_bytes:
    try:
        shopify_df = parse_shopify_csv(shopify_bytes)
        stripe_df = parse_stripe_csv(stripe_bytes)
        summary, metrics = reconcile_orders(shopify_df, stripe_df)

        st.markdown("### Reconciliation summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total gross revenue", f"${metrics['total_gross']:,.2f}")
        m2.metric("Estimated Stripe processing fees", f"${metrics['total_fees']:,.2f}")
        m3.metric("Net bank deposit", f"${metrics['net_deposit']:,.2f}")

        st.dataframe(summary, width="stretch", hide_index=True)

        st.download_button(
            label="Download clean CSV for QuickBooks (.csv)",
            data=summary_to_csv(summary, sep=";"),
            file_name="shopify_stripe_reconciliation.csv",
            mime="text/csv",
            type="primary",
        )
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        st.error("Something went wrong while reconciling your files. Please check your CSV exports and try again.")
elif shopify_bytes or stripe_bytes:
    st.info("Upload both CSV files — or click **Load Sample Data** — to run reconciliation.")
else:
    st.info(
        "Upload your Shopify orders export and Stripe balance/payout CSV, "
        "or load sample data to see a QuickBooks-ready reconciliation."
    )
