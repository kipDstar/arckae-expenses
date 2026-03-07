import os
from datetime import date, datetime
from typing import Optional
from uuid import uuid4

import streamlit as st


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")


def ensure_directories() -> None:
    """Ensure that core storage directories exist."""
    for path in (RECEIPTS_DIR, EXPORTS_DIR, BACKUPS_DIR):
        os.makedirs(path, exist_ok=True)


def format_kes(amount: Optional[float]) -> str:
    """Format a numeric value as Kenyan Shillings."""
    if amount is None:
        return "KES 0"
    try:
        return f"KES {amount:,.2f}"
    except (TypeError, ValueError):
        return "KES 0"


def to_iso_date(value: date | datetime | str) -> str:
    """Normalise a date-like value to ISO 8601 date string (YYYY-MM-DD)."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    # Assume already a string in acceptable format.
    return str(value)


def save_uploaded_file(uploaded_file: "st.runtime.uploaded_file_manager.UploadedFile", prefix: str) -> str:
    """
    Save an uploaded receipt file to the receipts directory with a standard name.

    The file name pattern is: {prefix}_YYYY_MM_DD_<unique>.ext
    """
    ensure_directories()

    original_name = uploaded_file.name
    _, ext = os.path.splitext(original_name)
    ext = ext.lower() or ".dat"

    today_str = datetime.now().strftime("%Y_%m_%d")
    unique = uuid4().hex[:8]
    filename = f"{prefix}_{today_str}_{unique}{ext}"

    target_path = os.path.join(RECEIPTS_DIR, filename)
    with open(target_path, "wb") as dest:
        dest.write(uploaded_file.getbuffer())

    return target_path

