## ArcKAE Finance – Developer Guide

This guide explains the **architecture and internals** of the ArcKAE Finance app.  
It is written for developers who are comfortable with basic Python and want to understand how the system works under the hood.

---

## 1. High-Level Architecture

ArcKAE Finance is a **single-page Streamlit application** split into logical modules:

- `app.py` – application entrypoint and page router
- `auth.py` – login helpers
- `database.py` – database access and persistence
- `utils.py` – shared utilities (file handling, directories, formatting)
- `dashboard.py` – overview KPIs and charts
- `expenses_page.py` – record and search expenses
- `revenue_page.py` – record and search revenues
- `financial_summary.py` – income statement style summaries
- `reports_page.py` – reporting and exports
- `launcher.py` – thin wrapper so PyInstaller can build a desktop-style executable

Data flows are:

1. **User actions in Streamlit** (forms/buttons) create or query data.
2. **Database helpers** in `database.py` read/write to `arckae_finance.db`.
3. **Pandas** is used to transform query results into DataFrames and to calculate aggregates.
4. **Plotly** turns those aggregates into interactive charts.
5. **Utils** functions handle currency formatting and file paths for receipts and exports.

The system is deliberately small and **modular**, so you can easily extend it.

---

## 2. Database Structure & Layer

### 2.1 Database File

The database is a **SQLite** file stored in the project root:

- `arckae_finance.db`

The database path is defined in `database.py`:

- `DB_PATH = os.path.join(BASE_DIR, "arckae_finance.db")`

### 2.2 Tables

1. **`users`**
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `username TEXT UNIQUE NOT NULL`
   - `password_hash TEXT NOT NULL`
   - `created_at TEXT NOT NULL`

2. **`expenses`**
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `date TEXT NOT NULL` – stored as `YYYY-MM-DD`
   - `supplier_name TEXT NOT NULL`
   - `supplier_kra_pin TEXT`
   - `etims_invoice_number TEXT`
   - `category TEXT NOT NULL`
   - `description TEXT`
   - `amount_kes REAL NOT NULL`
   - `payment_method TEXT NOT NULL`
   - `receipt_path TEXT`
   - `created_at TEXT NOT NULL`

3. **`revenues`**
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `date TEXT NOT NULL`
   - `client_name TEXT NOT NULL`
   - `service_type TEXT NOT NULL`
   - `description TEXT`
   - `amount_received REAL NOT NULL`
   - `payment_method TEXT NOT NULL`
   - `mpesa_reference TEXT`
   - `receipt_path TEXT`
   - `created_at TEXT NOT NULL`

### 2.3 Database Initialisation

Key functions in `database.py`:

- `get_connection() -> sqlite3.Connection`  
  Opens a connection to `arckae_finance.db` with `row_factory` set so rows behave like dicts.

- `_create_tables(conn)`  
  Executes `CREATE TABLE IF NOT EXISTS ...` SQL for all three tables.

- `ensure_default_admin(username="admin", password="admin123")`  
  Checks whether a user with that username exists; if not, hashes the password with **bcrypt** and inserts a new row.

- `init_db()`  
  Main entrypoint used by `app.py` on startup. Creates the database file (if missing), creates tables, and ensures the default admin exists.

### 2.4 Inserts and Updates

The write operations are small, explicit functions:

- `insert_expense(...) -> int`  
  Inserts a single expense row, returning the new `id`.

- `insert_revenue(...) -> int`  
  Inserts a single revenue row.

- `get_user_credentials(username) -> Optional[Tuple[str, str]]`  
  Retrieves the `(username, password_hash)` pair for auth.

- `update_user_password(username, new_password) -> bool`  
  Hashes the new password and updates the corresponding user row.

Each function opens a connection using `get_connection()`, runs the SQL within a context manager, and commits once the operation succeeds.

---

## 3. Authentication System

Authentication is handled by two modules:

- `database.py` – for reading and writing user records
- `auth.py` – for Streamlit UI and bcrypt verification

### 3.1 Password Hashing

`database.py` and `auth.py` both use **bcrypt**:

- When a user is created or their password is updated:
  - The plain password is encoded with UTF‑8.
  - `bcrypt.hashpw` produces a secure hash including salt.
  - The hash is decoded to a UTF‑8 string and stored in `users.password_hash`.

### 3.2 Verifying Passwords

`auth.verify_password(plain_password, password_hash)`:

- Encodes the plain password.
- Encodes the stored hash string.
- Calls `bcrypt.checkpw`.
- Returns `True` only if the password is correct.

### 3.3 Login Flow & Session State

`auth.render_login_page()`:

1. Renders username and password fields with Streamlit.
2. On submit:
   - Loads the stored hash via `database.get_user_credentials`.
   - Calls `verify_password` to validate the provided password.
   - If valid, sets:
     - `st.session_state.logged_in = True`
     - `st.session_state.username = <username>`
3. Any invalid attempt shows an error and leaves session state unchanged.

`app.py` checks `st.session_state.logged_in`:

- If `False` (or missing), only the **Login** page is accessible.
- Once logged in, all other pages become available via the sidebar.

The **Settings** page also uses `database.update_user_password` to let the logged‑in user change their password.

---

## 4. Financial Summary & Calculations

Financial calculations are based on **Pandas DataFrames** created from SQLite table queries.

### 4.1 Loading Data

Modules like `dashboard.py`, `financial_summary.py`, and `reports_page.py` follow the same pattern:

1. Call `get_connection()` from `database.py`.
2. Run `pd.read_sql_query("SELECT * FROM ...", conn)` to get a DataFrame.
3. Convert the `date` column to `datetime` using `pd.to_datetime`.

### 4.2 Core Calculations

Some examples of the calculations performed:

- **Totals**:
  - `total_revenue = revenues["amount_received"].sum()`
  - `total_expenses = expenses["amount_kes"].sum()`
  - `net_profit = total_revenue - total_expenses`

- **Current month metrics (Dashboard)**:
  - Convert `date` to `Period("M")` and filter rows matching the current month.

- **Category breakdown (Expenses)**:
  - `expenses.groupby("category")["amount_kes"].sum()`

- **Monthly revenue vs expenses**:
  - Add a derived `month` column from `date` (e.g. `"2026-03"`).
  - Group both expenses and revenues by `month`.
  - Join the results to build a table of `month`, `Revenue`, `Expenses`, `Net Profit`.

These calculations are then passed to **Plotly Express** (e.g. `px.pie`, `px.bar`, `px.line`) for visualisation.

### 4.3 Financial Summary Engine

`financial_summary.py` is responsible for the income statement view:

1. Loads expenses and revenues into DataFrames.
2. Lets the user choose a filter mode:
   - Month
   - Year
   - Custom Date Range
3. Computes the appropriate start and end dates.
4. Filters both DataFrames to that window.
5. Calculates:
   - Total Revenue in period
   - Total Expenses in period
   - Net Profit (or Net Loss)
6. Creates:
   - Pie chart for expense category breakdown.
   - Line chart for monthly net profit trend within the selected range.

All logic is **pure Pandas** and easy to extend if you need more derived metrics.

---

## 5. File Uploads and Storage

File handling is centralised in `utils.py`.

### 5.1 Directory Management

`utils.ensure_directories()`:

- Ensures that:
  - `receipts/`
  - `exports/`
  - `backups/`
  all exist.

`app.py` calls this at startup, so the folders are always created on demand.

### 5.2 Receipt Uploads

In `expenses_page.py` and `revenue_page.py`:

- Streamlit’s `st.file_uploader` accepts JPG, PNG, and PDF files.
- When a form is submitted:
  - If a file was uploaded, the page calls:
    - `utils.save_uploaded_file(uploaded_file, prefix=<"expense" or "revenue">)`
  - This function:
    - Generates a filename: `prefix_YYYY_MM_DD_<unique>.ext`
    - Saves the raw bytes into `receipts/`.
    - Returns the file path (saved in the database).

The database now holds only the path string; the binary data lives in the filesystem.

---

## 6. Reports and Exports

The `reports_page.py` module generates different kinds of reports using **Pandas**, and saves them to disk.

### 6.1 Types of Reports

1. **Expense Report**
   - Row‑level details of expenses in a chosen date range.
   - Includes supplier, KRA PIN, eTIMS invoice, category, description, KES amount, payment method, and receipt path.

2. **Revenue Report**
   - Row‑level details of revenues in a date range.
   - Includes client, service type, description, KES amount, payment method, Mpesa reference, and receipt path.

3. **Monthly Profit and Loss Report**
   - Aggregated by month.
   - Columns: `month`, `Revenue`, `Expenses`, `Net Profit`.

4. **Financial Summary Report**
   - High-level summary:
     - Total Revenue
     - Total Expenses
     - Net Profit
   - Plus an **expense breakdown by category**.

### 6.2 Export Formats

Users can export in:

- **CSV (`.csv`)**
- **Excel (`.xlsx`)** using `openpyxl` under the hood

`reports_page._save_report()`:

- Receives the DataFrame, a base filename, and desired format.
- Builds a timestamped filename, e.g. `expense_report_20260307_120000.csv`.
- Ensures `exports/` exists.
- Saves the file to disk (for CSV or Excel).
- Returns both the **path on disk** and the **bytes** for Streamlit’s download button.

This design keeps exported files:

- Persisted locally under `exports/`.
- Immediately downloadable through the UI.

---

## 7. Automatic Database Backups

`database.backup_database()`:

- Checks if `arckae_finance.db` exists.
- Ensures `backups/` exists.
- Copies the current database file to:
  - `backups/arckae_backup_YYYY_MM_DD.db`

`app.py` calls `backup_database()` on startup.  
If you start the app multiple times in a day, the same day’s backup is overwritten, which keeps backups **simple and predictable**.

You can extend this function if you want versioned backups (e.g. with timestamps) or automatic pruning.

---

## 8. Application Entry and Navigation

### 8.1 `app.py`

`app.py` is the main entrypoint for Streamlit:

1. Calls `st.set_page_config` to set the title and layout.
2. Calls `_init_app()`:
   - `ensure_directories()`
   - `init_db()`
   - `backup_database()`
3. Initialises `st.session_state` with:
   - `logged_in`
   - `username`
4. Renders the sidebar navigation:
   - Shows the current username.
   - Provides a **Log out** button for authenticated users.
   - Uses `st.radio` to choose a page from:
     - Login, Dashboard, Record Expense, Record Revenue, Expense Search,
       Revenue Search, Financial Summary, Reports, Settings.
5. If the user is not logged in and selects any page other than Login, the app:
   - Forces the page back to **Login**.

Each page is implemented as a `render_*` function imported from its respective module.

### 8.2 Settings Page

The Settings page (implemented in `app.py`) allows:

- Viewing the current logged‑in username.
- Changing the password:
  - Verifies the current password using bcrypt.
  - On success, updates the hash via `database.update_user_password`.

---

## 9. EXE Packaging Process

The project is designed to be packaged as a **standalone Windows executable** using **PyInstaller**.

### 9.1 `launcher.py`

`launcher.py` is intentionally simple:

- It imports `sys` and `subprocess`.
- Its `main()` function calls:

  ```python
  subprocess.run(
      [sys.executable, "-m", "streamlit", "run", "app.py"],
      check=False,
  )
  ```

When you compile `launcher.py` with PyInstaller, the resulting `.exe` runs this script, which in turn starts Streamlit.

### 9.2 Building the Executable

From the project root:

```bash
pip install pyinstaller  # if not already installed
pyinstaller --onefile --noconsole launcher.py
```

PyInstaller produces:

- `dist/launcher.exe`

You can then rename this to:

- `ArcKAE-Finance.exe`

When a user double‑clicks `ArcKAE-Finance.exe`:

1. The embedded Python runtime starts.
2. `launcher.py` runs and executes the Streamlit CLI.
3. Streamlit opens the ArcKAE Finance app in the user’s default browser.

No manual Python installation is needed on the user’s machine.

---

## 10. Extending the System

Here are a few common extension ideas and where to start:

- **New expense or revenue fields**  
  - Update the SQLite schema in `database.py` (add columns and migrations).
  - Update forms in `expenses_page.py` or `revenue_page.py`.
  - Adjust reports in `reports_page.py` if necessary.

- **Additional user roles or permissions**  
  - Extend the `users` table (e.g. add `role` column).
  - Add role checks in `app.py` before rendering certain pages.

- **More complex reports**  
  - Add new functions in `reports_page.py` that build additional DataFrames.
  - Wire them into the report type dropdown and export flow.

- **Multiple environments (dev/test/prod)**  
  - Parameterise the database path using environment variables.
  - For example, allow `DB_PATH` to be overridden from an environment setting.

Because everything is written in standard Python with well-known libraries, you can safely refactor and extend the codebase as your needs grow.

