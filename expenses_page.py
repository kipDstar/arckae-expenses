import streamlit as st
import pandas as pd

from database import get_connection, insert_expense
from utils import format_kes, save_uploaded_file, to_iso_date


EXPENSE_CATEGORIES = [
    "Rent",
    "Salaries",
    "Marketing",
    "Utilities",
    "Office Supplies",
    "Travel",
    "Technology",
    "Consultancy",
    "Other",
]

PAYMENT_METHODS = [
    "Cash",
    "Bank Transfer",
    "Mpesa",
    "Card",
]


def render_record_expense() -> None:
    """Render the form used to capture a new business expense."""
    st.title("Record Expense")
    st.caption("Capture business expenses with supporting receipts for KRA compliance.")

    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            supplier_name = st.text_input("Supplier Name")
            supplier_kra_pin = st.text_input("Supplier KRA PIN")
            etims_invoice_number = st.text_input("eTIMS Invoice Number")
            category = st.selectbox("Category", EXPENSE_CATEGORIES)
        with col2:
            amount_kes = st.number_input("Amount (KES)", min_value=0.0, step=100.0, format="%.2f")
            payment_method = st.selectbox("Payment Method", PAYMENT_METHODS)
            description = st.text_area("Description", height=100)
            receipt_file = st.file_uploader(
                "Upload Receipt (JPG, PNG, PDF)",
                type=["jpg", "jpeg", "png", "pdf"],
            )

        submitted = st.form_submit_button("Save Expense", type="primary")

    if submitted:
        if amount_kes <= 0:
            st.error("Amount must be greater than zero.")
            return
        if not supplier_name:
            st.error("Supplier name is required.")
            return

        receipt_path = None
        if receipt_file is not None:
            receipt_path = save_uploaded_file(receipt_file, prefix="expense")

        try:
            insert_expense(
                date=to_iso_date(date),
                supplier_name=supplier_name.strip(),
                supplier_kra_pin=supplier_kra_pin.strip(),
                etims_invoice_number=etims_invoice_number.strip(),
                category=category,
                description=description.strip(),
                amount_kes=float(amount_kes),
                payment_method=payment_method,
                receipt_path=receipt_path,
            )
            st.success("Expense recorded successfully.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to save expense: {exc}")


def _load_expenses() -> pd.DataFrame:
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM expenses ORDER BY date DESC", conn)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def render_expense_search() -> None:
    """Render the search and filter page for expenses."""
    st.title("Expense Search")
    st.caption("Search and filter expenses by date, category, and supplier.")

    df = _load_expenses()
    if df.empty:
        st.info("No expenses recorded yet.")
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
            category = st.multiselect("Category", options=EXPENSE_CATEGORIES)

        supplier_query = st.text_input("Supplier Name Contains")

    mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    if category:
        mask &= df["category"].isin(category)
    if supplier_query:
        mask &= df["supplier_name"].str.contains(supplier_query, case=False, na=False)

    filtered = df.loc[mask].copy()
    filtered["Amount (KES)"] = filtered["amount_kes"].apply(format_kes)

    st.write(f"Showing **{len(filtered)}** matching expenses.")
    display_cols = [
        "date",
        "supplier_name",
        "supplier_kra_pin",
        "etims_invoice_number",
        "category",
        "description",
        "Amount (KES)",
        "payment_method",
        "receipt_path",
    ]
    st.dataframe(filtered[display_cols], use_container_width=True)

