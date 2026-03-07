import io
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from database import get_connection
from utils import EXPORTS_DIR, ensure_directories, format_kes


def _load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    with get_connection() as conn:
        expenses = pd.read_sql_query("SELECT * FROM expenses ORDER BY date", conn)
        revenues = pd.read_sql_query("SELECT * FROM revenues ORDER BY date", conn)

    if not expenses.empty:
        expenses["date"] = pd.to_datetime(expenses["date"])
    if not revenues.empty:
        revenues["date"] = pd.to_datetime(revenues["date"])

    return expenses, revenues


def _filter_range(df: pd.DataFrame, start, end, date_column: str = "date") -> pd.DataFrame:
    if df.empty:
        return df
    mask = (df[date_column].dt.date >= start) & (df[date_column].dt.date <= end)
    return df.loc[mask].copy()


def _expense_report(expenses: pd.DataFrame) -> pd.DataFrame:
    df = expenses.copy()
    if df.empty:
        return df
    df["Amount (KES)"] = df["amount_kes"].apply(format_kes)
    return df[
        [
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
    ]


def _revenue_report(revenues: pd.DataFrame) -> pd.DataFrame:
    df = revenues.copy()
    if df.empty:
        return df
    df["Amount (KES)"] = df["amount_received"].apply(format_kes)
    return df[
        [
            "date",
            "client_name",
            "service_type",
            "description",
            "Amount (KES)",
            "payment_method",
            "mpesa_reference",
            "receipt_path",
        ]
    ]


def _monthly_pnl_report(expenses: pd.DataFrame, revenues: pd.DataFrame) -> pd.DataFrame:
    if expenses.empty and revenues.empty:
        return pd.DataFrame(columns=["month", "Revenue", "Expenses", "Net Profit"])

    exp_monthly = (
        expenses.assign(month=expenses["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["amount_kes"]
        .sum()
    ) if not expenses.empty else pd.DataFrame(columns=["month", "amount_kes"])

    rev_monthly = (
        revenues.assign(month=revenues["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["amount_received"]
        .sum()
    ) if not revenues.empty else pd.DataFrame(columns=["month", "amount_received"])

    all_months = sorted(set(exp_monthly.get("month", pd.Series()).tolist()) | set(rev_monthly.get("month", pd.Series()).tolist()))
    rows = []
    for m in all_months:
        rev_val = float(rev_monthly.loc[rev_monthly["month"] == m, "amount_received"].sum()) if not rev_monthly.empty else 0.0
        exp_val = float(exp_monthly.loc[exp_monthly["month"] == m, "amount_kes"].sum()) if not exp_monthly.empty else 0.0
        rows.append({"month": m, "Revenue": rev_val, "Expenses": exp_val, "Net Profit": rev_val - exp_val})

    return pd.DataFrame(rows)


def _financial_summary_report(expenses: pd.DataFrame, revenues: pd.DataFrame) -> pd.DataFrame:
    total_revenue = float(revenues["amount_received"].sum()) if not revenues.empty else 0.0
    total_expenses = float(expenses["amount_kes"].sum()) if not expenses.empty else 0.0
    net_profit = total_revenue - total_expenses

    breakdown = (
        expenses.groupby("category", as_index=False)["amount_kes"]
        .sum()
        .rename(columns={"amount_kes": "amount"})
    ) if not expenses.empty else pd.DataFrame(columns=["category", "amount"])

    rows = [
        {"Metric": "Total Revenue", "Value": format_kes(total_revenue)},
        {"Metric": "Total Expenses", "Value": format_kes(total_expenses)},
        {"Metric": "Net Profit", "Value": format_kes(net_profit)},
    ]
    summary_df = pd.DataFrame(rows)

    if not breakdown.empty:
        breakdown["Value"] = breakdown["amount"].apply(format_kes)
        breakdown_df = breakdown[["category", "Value"]].rename(columns={"category": "Expense Category"})
        # Combine into a multi-section style summary stacked vertically.
        spacer = pd.DataFrame([{"Metric": "", "Value": ""}])
        summary_df = pd.concat(
            [
                summary_df,
                spacer,
                pd.DataFrame([{"Metric": "Expense Breakdown by Category", "Value": ""}]),
                breakdown_df.rename(columns={"Expense Category": "Metric"}),
            ],
            ignore_index=True,
        )

    return summary_df


def _save_report(df: pd.DataFrame, base_name: str, export_format: str) -> tuple[str, bytes]:
    """Save a DataFrame to disk and return (path, bytes_for_download)."""
    ensure_directories()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if export_format == "CSV":
        filename = f"{base_name}_{timestamp}.csv"
        path = os.path.join(EXPORTS_DIR, filename)
        df.to_csv(path, index=False)
        data = df.to_csv(index=False).encode("utf-8")
    else:
        filename = f"{base_name}_{timestamp}.xlsx"
        path = os.path.join(EXPORTS_DIR, filename)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Report")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Report")
        data = buffer.getvalue()

    return path, data


def render_reports_page() -> None:
    """Render the reports page with export capabilities."""
    st.title("Reports & Exports")
    st.caption("Generate KRA-ready financial reports and export them to CSV or Excel.")

    expenses, revenues = _load_data()
    if expenses.empty and revenues.empty:
        st.info("No financial data available yet.")
        return

    all_dates = pd.concat(
        [
            expenses["date"] if not expenses.empty else pd.Series(dtype="datetime64[ns]"),
            revenues["date"] if not revenues.empty else pd.Series(dtype="datetime64[ns]"),
        ]
    )
    min_date = all_dates.min().date()
    max_date = all_dates.max().date()

    with st.expander("Report Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        with col2:
            end = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
        if start > end:
            st.error("Start date must be before end date.")
            return

        report_type = st.selectbox(
            "Report Type",
            [
                "Expense Report",
                "Revenue Report",
                "Monthly Profit and Loss Report",
                "Financial Summary Report",
            ],
        )

        export_format = st.selectbox(
            "Export Format",
            ["Excel (.xlsx)", "CSV (.csv)"],
        )

    expenses_range = _filter_range(expenses, start, end)
    revenues_range = _filter_range(revenues, start, end)

    if report_type == "Expense Report":
        df_report = _expense_report(expenses_range)
        base_name = "expense_report"
    elif report_type == "Revenue Report":
        df_report = _revenue_report(revenues_range)
        base_name = "revenue_report"
    elif report_type == "Monthly Profit and Loss Report":
        df_report = _monthly_pnl_report(expenses_range, revenues_range)
        base_name = "monthly_pnl_report"
    else:
        df_report = _financial_summary_report(expenses_range, revenues_range)
        base_name = "financial_summary_report"

    if df_report.empty:
        st.warning("No data available for the selected filters.")
        return

    st.subheader("Preview")
    st.dataframe(df_report, use_container_width=True)

    export_label = "CSV" if export_format.endswith(".csv") else "Excel"
    if st.button(f"Export {report_type} as {export_label}", type="primary"):
        fmt = "CSV" if export_format.endswith(".csv") else "Excel"
        path, data = _save_report(df_report, base_name, fmt)
        st.success(f"Report exported to `{path}`.")
        st.download_button(
            "Download Now",
            data=data,
            file_name=os.path.basename(path),
            mime="text/csv" if fmt == "CSV" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

