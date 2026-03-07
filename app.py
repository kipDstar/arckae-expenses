import streamlit as st

from auth import render_login_page
from database import backup_database, init_db
from utils import ensure_directories

import dashboard
import expenses_page
import revenue_page
import financial_summary
import reports_page


PAGES = [
    "Login",
    "Dashboard",
    "Record Expense",
    "Record Revenue",
    "Expense Search",
    "Revenue Search",
    "Financial Summary",
    "Reports",
    "Settings",
]


def _init_app() -> None:
    """Initialise infrastructure required for the app to run."""
    ensure_directories()
    init_db()
    backup_database()


def _init_session_state() -> None:
    """Seed Streamlit session_state keys used by the app."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None


def _render_settings_page() -> None:
    """Simple settings page for account management."""
    from database import update_user_password, get_user_credentials
    import bcrypt

    st.title("Settings")
    st.subheader("Account")

    if not st.session_state.get("logged_in"):
        st.info("Log in to manage your account settings.")
        return

    username = st.session_state.get("username")
    st.write(f"Logged in as **{username}**")

    with st.expander("Change Password"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")

        if st.button("Update Password"):
            if not current_password or not new_password:
                st.error("Please fill in all password fields.")
            elif new_password != confirm_password:
                st.error("New passwords do not match.")
            else:
                creds = get_user_credentials(username)
                if creds is None:
                    st.error("Could not load current user from database.")
                else:
                    _, stored_hash = creds
                    if not bcrypt.checkpw(current_password.encode("utf-8"), stored_hash.encode("utf-8")):
                        st.error("Current password is incorrect.")
                    else:
                        if update_user_password(username, new_password):
                            st.success("Password updated successfully.")
                        else:
                            st.error("Failed to update password.")


def main() -> None:
    st.set_page_config(
        page_title="ArcKAE Finance",
        page_icon="💼",
        layout="wide",
    )

    _init_app()
    _init_session_state()

    with st.sidebar:
        st.title("ArcKAE Finance")

        if st.session_state.logged_in:
            st.caption(f"Logged in as {st.session_state.username}")
            if st.button("Log out"):
                st.session_state.logged_in = False
                st.session_state.username = None

        selected_page = st.radio("Navigation", PAGES, index=0)

    if not st.session_state.logged_in and selected_page != "Login":
        st.warning("You must log in before accessing the finance dashboard.")
        selected_page = "Login"

    if selected_page == "Login":
        render_login_page()
    elif selected_page == "Dashboard":
        dashboard.render_dashboard()
    elif selected_page == "Record Expense":
        expenses_page.render_record_expense()
    elif selected_page == "Expense Search":
        expenses_page.render_expense_search()
    elif selected_page == "Record Revenue":
        revenue_page.render_record_revenue()
    elif selected_page == "Revenue Search":
        revenue_page.render_revenue_search()
    elif selected_page == "Financial Summary":
        financial_summary.render_financial_summary()
    elif selected_page == "Reports":
        reports_page.render_reports_page()
    elif selected_page == "Settings":
        _render_settings_page()


if __name__ == "__main__":
    main()

