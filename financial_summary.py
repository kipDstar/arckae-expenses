import calendar
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_connection
from utils import format_kes


def _load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    with get_connection() as conn:
        expenses = pd.read_sql_query("SELECT * FROM expenses ORDER BY date", conn)
        revenues = pd.read_sql_query("SELECT * FROM revenues ORDER BY date", conn)

    if not expenses.empty:
        expenses["date"] = pd.to_datetime(expenses["date"])
    if not revenues.empty:
        revenues["date"] = pd.to_datetime(revenues["date"])

    return expenses, revenues


def _filter_by_range(
    expenses: pd.DataFrame,
    revenues: pd.DataFrame,
    start: date,
    end: date,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    exp = expenses[
        (expenses["date"].dt.date >= start)
        & (expenses["date"].dt.date <= end)
    ].copy()
    rev = revenues[
        (revenues["date"].dt.date >= start)
        & (revenues["date"].dt.date <= end)
    ].copy()
    return exp, rev


def render_financial_summary() -> None:
    """Render an income-statement style financial summary for a selected period."""
    st.title("Financial Summary")
    st.caption("Income statement style overview of revenue, expenses, and net profit/loss.")

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

    st.subheader("Filter Period")
    mode = st.radio(
        "Select filter type",
        ["Month", "Year", "Custom Date Range"],
        horizontal=True,
    )

    if mode == "Month":
        years = sorted({d.year for d in all_dates.dt.date})
        default_year = max(years)
        year = st.selectbox("Year", options=years, index=years.index(default_year))
        months = list(range(1, 13))
        current_month = max_date.month
        month = st.selectbox(
            "Month",
            options=months,
            format_func=lambda m: f"{m:02d} - {calendar.month_name[m]}",
            index=current_month - 1,
        )
        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)
    elif mode == "Year":
        years = sorted({d.year for d in all_dates.dt.date})
        default_year = max(years)
        year = st.selectbox("Year", options=years, index=years.index(default_year))
        start = date(year, 1, 1)
        end = date(year, 12, 31)
    else:  # Custom Date Range
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        with col2:
            end = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
        if start > end:
            st.error("Start date must be before end date.")
            return

    exp_period, rev_period = _filter_by_range(expenses, revenues, start, end)

    total_revenue = float(rev_period["amount_received"].sum()) if not rev_period.empty else 0.0
    total_expenses = float(exp_period["amount_kes"].sum()) if not exp_period.empty else 0.0
    net_profit = total_revenue - total_expenses

    st.markdown("### Income Statement Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Revenue", format_kes(total_revenue))
    with col2:
        st.metric("Total Expenses", format_kes(total_expenses))
    with col3:
        label = "Net Profit" if net_profit >= 0 else "Net Loss"
        st.metric(label, format_kes(net_profit))

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Expense Breakdown by Category")
        if exp_period.empty:
            st.write("No expenses in the selected period.")
        else:
            by_category = (
                exp_period.groupby("category", as_index=False)["amount_kes"]
                .sum()
                .rename(columns={"amount_kes": "amount"})
            )
            fig = px.pie(
                by_category,
                names="category",
                values="amount",
                title="Expenses by Category",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Monthly Profit Trend")
        if exp_period.empty and rev_period.empty:
            st.write("No data in the selected period.")
        else:
            exp_monthly = (
                exp_period.assign(month=exp_period["date"].dt.to_period("M").astype(str))
                .groupby("month", as_index=False)["amount_kes"]
                .sum()
            ) if not exp_period.empty else pd.DataFrame(columns=["month", "amount_kes"])

            rev_monthly = (
                rev_period.assign(month=rev_period["date"].dt.to_period("M").astype(str))
                .groupby("month", as_index=False)["amount_received"]
                .sum()
            ) if not rev_period.empty else pd.DataFrame(columns=["month", "amount_received"])

            all_months = sorted(set(exp_monthly.get("month", pd.Series()).tolist()) | set(rev_monthly.get("month", pd.Series()).tolist()))
            rows = []
            for m in all_months:
                rev_val = float(rev_monthly.loc[rev_monthly["month"] == m, "amount_received"].sum()) if not rev_monthly.empty else 0.0
                exp_val = float(exp_monthly.loc[exp_monthly["month"] == m, "amount_kes"].sum()) if not exp_monthly.empty else 0.0
                rows.append({"month": m, "Net Profit": rev_val - exp_val})

            trend_df = pd.DataFrame(rows)
            if not trend_df.empty:
                fig_trend = px.line(
                    trend_df,
                    x="month",
                    y="Net Profit",
                    title="Monthly Net Profit Trend",
                    labels={"month": "Month", "Net Profit": "Net Profit (KES)"},
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.write("No monthly trend to display.")

