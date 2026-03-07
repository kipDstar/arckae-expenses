import streamlit as st
import pandas as pd
import plotly.express as px

from database import get_connection
from utils import format_kes


def _load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load expenses and revenues into DataFrames."""
    with get_connection() as conn:
        expenses = pd.read_sql_query("SELECT * FROM expenses ORDER BY date", conn)
        revenues = pd.read_sql_query("SELECT * FROM revenues ORDER BY date", conn)

    if not expenses.empty:
        expenses["date"] = pd.to_datetime(expenses["date"])
    if not revenues.empty:
        revenues["date"] = pd.to_datetime(revenues["date"])

    return expenses, revenues


def _current_month_masks(expenses: pd.DataFrame, revenues: pd.DataFrame):
    today = pd.Timestamp.today()
    current_period = today.to_period("M")

    exp_mask = expenses["date"].dt.to_period("M") == current_period if not expenses.empty else pd.Series(dtype=bool)
    rev_mask = revenues["date"].dt.to_period("M") == current_period if not revenues.empty else pd.Series(dtype=bool)
    return exp_mask, rev_mask


def render_dashboard() -> None:
    """Render the main financial dashboard."""
    st.title("Financial Dashboard")
    st.caption("High-level overview of ArcKAE's monthly performance.")

    expenses, revenues = _load_data()

    if expenses.empty and revenues.empty:
        st.info("No financial data available yet. Start by recording expenses and revenues.")
        return

    exp_mask, rev_mask = _current_month_masks(expenses, revenues)

    total_expenses_month = float(expenses.loc[exp_mask, "amount_kes"].sum()) if not expenses.empty else 0.0
    total_revenue_month = float(revenues.loc[rev_mask, "amount_received"].sum()) if not revenues.empty else 0.0
    net_profit_month = total_revenue_month - total_expenses_month

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Revenue (Current Month)", format_kes(total_revenue_month))
    with col2:
        st.metric("Total Expenses (Current Month)", format_kes(total_expenses_month))
    with col3:
        label = "Net Profit (Current Month)" if net_profit_month >= 0 else "Net Loss (Current Month)"
        st.metric(label, format_kes(net_profit_month))

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Expense Breakdown by Category")
        if expenses.empty:
            st.write("No expenses recorded.")
        else:
            by_category = expenses.groupby("category", as_index=False)["amount_kes"].sum()
            fig = px.pie(
                by_category,
                names="category",
                values="amount_kes",
                title="Expenses by Category",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Revenue vs Expenses by Month")
        if expenses.empty and revenues.empty:
            st.write("No data available.")
        else:
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
            summary_rows = []
            for m in all_months:
                rev_val = float(rev_monthly.loc[rev_monthly["month"] == m, "amount_received"].sum()) if not rev_monthly.empty else 0.0
                exp_val = float(exp_monthly.loc[exp_monthly["month"] == m, "amount_kes"].sum()) if not exp_monthly.empty else 0.0
                summary_rows.append({"month": m, "Revenue": rev_val, "Expenses": exp_val})

            monthly_df = pd.DataFrame(summary_rows)
            if not monthly_df.empty:
                melt_df = monthly_df.melt(id_vars="month", value_vars=["Revenue", "Expenses"], var_name="Type", value_name="Amount")
                fig_bar = px.bar(
                    melt_df,
                    x="month",
                    y="Amount",
                    color="Type",
                    barmode="group",
                    title="Monthly Revenue vs Expenses",
                    labels={"month": "Month", "Amount": "Amount (KES)"},
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.write("No monthly data to display yet.")

    st.markdown("---")

    st.subheader("Cashflow Trend")
    if expenses.empty and revenues.empty:
        st.write("No data available.")
    else:
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
            rows.append({"month": m, "Net Cashflow": rev_val - exp_val})

        cf_df = pd.DataFrame(rows)
        if not cf_df.empty:
            fig_cf = px.line(
                cf_df,
                x="month",
                y="Net Cashflow",
                title="Monthly Cashflow Trend (Revenue - Expenses)",
                labels={"month": "Month", "Net Cashflow": "Net Cashflow (KES)"},
            )
            st.plotly_chart(fig_cf, use_container_width=True)
        else:
            st.write("No cashflow data to display yet.")

