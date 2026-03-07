import streamlit as st
import pandas as pd

from database import get_connection, insert_revenue
from utils import format_kes, save_uploaded_file, to_iso_date


PAYMENT_METHODS = [
    "Cash",
    "Bank Transfer",
    "Mpesa",
    "Card",
]


def render_record_revenue() -> None:
    """Render the form used to record client revenue."""
    st.title("Record Revenue")
    st.caption("Capture revenue received from ArcKAE clients, including Mpesa references.")

    with st.form("revenue_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            client_name = st.text_input("Client Name")
            service_type = st.text_input("Service Type")
            amount_received = st.number_input("Amount Received (KES)", min_value=0.0, step=100.0, format="%.2f")
        with col2:
            payment_method = st.selectbox("Payment Method", PAYMENT_METHODS)
            mpesa_reference = st.text_input("Mpesa Reference")
            description = st.text_area("Description", height=100)
            receipt_file = st.file_uploader(
                "Upload Payment Receipt (JPG, PNG, PDF)",
                type=["jpg", "jpeg", "png", "pdf"],
            )

        submitted = st.form_submit_button("Save Revenue", type="primary")

    if submitted:
        if amount_received <= 0:
            st.error("Amount received must be greater than zero.")
            return
        if not client_name:
            st.error("Client name is required.")
            return
        if not service_type:
            st.error("Service type is required.")
            return

        receipt_path = None
        if receipt_file is not None:
            receipt_path = save_uploaded_file(receipt_file, prefix="revenue")

        try:
            insert_revenue(
                date=to_iso_date(date),
                client_name=client_name.strip(),
                service_type=service_type.strip(),
                description=description.strip(),
                amount_received=float(amount_received),
                payment_method=payment_method,
                mpesa_reference=mpesa_reference.strip(),
                receipt_path=receipt_path,
            )
            st.success("Revenue recorded successfully.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to save revenue: {exc}")


def _load_revenues() -> pd.DataFrame:
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM revenues ORDER BY date DESC", conn)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def render_revenue_search() -> None:
    """Render the search and filter page for revenues."""
    st.title("Revenue Search")
    st.caption("Search and filter revenues by date, client, and payment method.")

    df = _load_revenues()
    if df.empty:
        st.info("No revenues recorded yet.")
        return

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    with st.expander("Filters", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
        with col3:
            payment_method_filter = st.multiselect("Payment Method", options=PAYMENT_METHODS)

        client_query = st.text_input("Client Name Contains")

    mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    if payment_method_filter:
        mask &= df["payment_method"].isin(payment_method_filter)
    if client_query:
        mask &= df["client_name"].str.contains(client_query, case=False, na=False)

    filtered = df.loc[mask].copy()
    filtered["Amount (KES)"] = filtered["amount_received"].apply(format_kes)

    st.write(f"Showing **{len(filtered)}** matching revenues.")
    display_cols = [
        "date",
        "client_name",
        "service_type",
        "description",
        "Amount (KES)",
        "payment_method",
        "mpesa_reference",
        "receipt_path",
    ]
    st.dataframe(filtered[display_cols], use_container_width=True)

