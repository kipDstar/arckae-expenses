import os
import sqlite3
import shutil
from datetime import datetime
from typing import Optional, Tuple

import bcrypt


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arckae_finance.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    """Create core tables if they do not exist."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            supplier_kra_pin TEXT,
            etims_invoice_number TEXT,
            category TEXT NOT NULL,
            description TEXT,
            amount_kes REAL NOT NULL,
            payment_method TEXT NOT NULL,
            receipt_path TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS revenues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            client_name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            description TEXT,
            amount_received REAL NOT NULL,
            payment_method TEXT NOT NULL,
            mpesa_reference TEXT,
            receipt_path TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    conn.commit()


def _get_user_by_username(conn: sqlite3.Connection, username: str) -> Optional[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cursor.fetchone()


def _create_user(conn: sqlite3.Connection, username: str, password: str) -> int:
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    created_at = datetime.utcnow().isoformat()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (username, password_hash, created_at)
        VALUES (?, ?, ?)
        """,
        (username, password_hash, created_at),
    )
    conn.commit()
    return cursor.lastrowid


def ensure_default_admin(username: str = "admin", password: str = "admin123") -> None:
    """
    Ensure there is at least one admin user.

    For simplicity, this creates a single default admin user on first run.
    The credentials should be changed from the Settings page after first login.
    """
    with get_connection() as conn:
        existing = _get_user_by_username(conn, username)
        if existing is None:
            _create_user(conn, username, password)


def init_db() -> None:
    """Initialise the database and create a default admin user if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        _create_tables(conn)
    ensure_default_admin()


def backup_database() -> Optional[str]:
    """
    Create a dated backup of the SQLite database.

    Returns the backup file path if created, or None if the database does not yet exist.
    """
    if not os.path.exists(DB_PATH):
        # Nothing to back up yet.
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_name = f"arckae_backup_{datetime.now().strftime('%Y_%m_%d')}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def insert_expense(
    date: str,
    supplier_name: str,
    supplier_kra_pin: str,
    etims_invoice_number: str,
    category: str,
    description: str,
    amount_kes: float,
    payment_method: str,
    receipt_path: Optional[str] = None,
) -> int:
    """Insert a new expense record and return its ID."""
    created_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO expenses (
                date,
                supplier_name,
                supplier_kra_pin,
                etims_invoice_number,
                category,
                description,
                amount_kes,
                payment_method,
                receipt_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                supplier_name,
                supplier_kra_pin,
                etims_invoice_number,
                category,
                description,
                amount_kes,
                payment_method,
                receipt_path,
                created_at,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def insert_revenue(
    date: str,
    client_name: str,
    service_type: str,
    description: str,
    amount_received: float,
    payment_method: str,
    mpesa_reference: str,
    receipt_path: Optional[str] = None,
) -> int:
    """Insert a new revenue record and return its ID."""
    created_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO revenues (
                date,
                client_name,
                service_type,
                description,
                amount_received,
                payment_method,
                mpesa_reference,
                receipt_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                client_name,
                service_type,
                description,
                amount_received,
                payment_method,
                mpesa_reference,
                receipt_path,
                created_at,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_user_credentials(username: str) -> Optional[Tuple[str, str]]:
    """
    Convenience helper for authentication.

    Returns (username, password_hash) if the user exists, else None.
    """
    with get_connection() as conn:
        row = _get_user_by_username(conn, username)
        if row is None:
            return None
        return row["username"], row["password_hash"]


def update_user_password(username: str, new_password: str) -> bool:
    """
    Update the password hash for a given user.

    Returns True if the user existed and was updated.
    """
    with get_connection() as conn:
        existing = _get_user_by_username(conn, username)
        if existing is None:
            return False

        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
        conn.commit()
        return cursor.rowcount > 0

