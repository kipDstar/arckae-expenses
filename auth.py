import streamlit as st
import bcrypt

from database import get_user_credentials


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        # If the stored hash is somehow invalid, fail closed.
        return False


def render_login_page() -> None:
    """Render the login form and manage session state on success."""
    st.title("ArcKAE Finance Login")
    st.write(
        "Please sign in with your ArcKAE finance account. "
        "On first run, use the default admin credentials documented in the README."
    )

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log In", type="primary"):
        username = username.strip()
        if not username or not password:
            st.error("Please enter both username and password.")
            return

        credentials = get_user_credentials(username)
        if credentials is None:
            st.error("Invalid username or password.")
            return

        _, stored_hash = credentials
        if verify_password(password, stored_hash):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login successful.")
        else:
            st.error("Invalid username or password.")

