## ArcKAE Finance – Local Finance Tracking App

ArcKAE Finance is a **local desktop-style finance tracking application** built for **ARCKAE** Education Agency LTD  
It runs as a **Streamlit app in the browser** and stores all data locally in a **SQLite** database.

The system tracks:

- **Business expenses**
- **Client revenue payments**
- **Financial receipts and invoices**
- **Monthly profit and loss**
- **Financial summaries**
- **KRA‑ready export reports**

The goal is a **clean, maintainable, and transparent financial system**.

---

## 1. Technology Stack

- **Python**
- **Streamlit** – UI framework
- **SQLite3** – local database
- **Pandas** – data processing and aggregations
- **Plotly** – interactive charts
- **bcrypt** – password hashing
- **openpyxl** – Excel exports

Everything runs locally; no external cloud services (could be a stretch goal for scale)

---

## 2. Project Structure

At the project root (`arckae-finance` style layout):

- `app.py` – main Streamlit application, navigation, and page wiring
- `database.py` – SQLite database creation, migrations, and data access helpers
- `auth.py` – login/authentication helpers using bcrypt
- `dashboard.py` – main financial dashboard (KPIs and charts)
- `expenses_page.py` – record expenses + expense search
- `revenue_page.py` – record revenue + revenue search
- `financial_summary.py` – income-statement style summaries
- `reports_page.py` – exportable reports (CSV/Excel)
- `utils.py` – shared helpers (currency formatting, file handling, directories)
- `launcher.py` – entrypoint used for the Windows `.exe`

Storage folders (created automatically if missing):

- `receipts/` – uploaded expense and revenue receipt files
- `exports/` – generated CSV / Excel reports
- `backups/` – automatic database backups

Supporting files:

- `requirements.txt` – Python dependencies
- `README.md` – high-level usage and concepts (this file)
- `DEVELOPER_GUIDE.md` – architecture and implementation details for developers

---

## 3. Database & Data Storage

### 3.1 SQLite Database

The app uses a single SQLite database file:

- **File**: `arckae_finance.db`

Tables:

- `users`
  - `id`, `username`, `password_hash`, `created_at`
  - Used for **login authentication**
  - Passwords are stored as **bcrypt hashes** (never plain-text)
- `expenses`
  - `id`, `date`, `supplier_name`, `supplier_kra_pin`, `etims_invoice_number`,
  `category`, `description`, `amount_kes`, `payment_method`,
  `receipt_path`, `created_at`
- `revenues`
  - `id`, `date`, `client_name`, `service_type`, `description`,
  `amount_received`, `payment_method`, `mpesa_reference`,
  `receipt_path`, `created_at`

The schema is created automatically on first run by `database.init_db()`.

### 3.2 Automatic Database Backup

When you start the application:

- The app creates (or verifies) the folder: `backups/`
- A backup copy of `arckae_finance.db` is written as:
  - `backups/arckae_backup_YYYY_MM_DD.db`

If you start the app multiple times on the same day, the backup file for that day will be replaced, ensuring you always have a **recent daily snapshot**.

---

## 4. Authentication & Login

### 4.1 Users Table and Password Hashing

- All users are stored in the `users` table.
- Passwords are hashed using **bcrypt** before being written to the database.
- Login checks are done by verifying the hashed password; the plain password is never stored.

### 4.2 Default Admin User

On the very first run, if there are no users, the system creates a default admin:

- **Username**: `admin`
- **Password**: `admin123`

You should log in with these credentials and **change the password** via the **Settings** page as soon as possible.

### 4.3 Login Flow

1. When you open the app, you see the **Login** page.
2. Enter your username and password.
3. On success:
  - Streamlit’s `session_state` is updated with `logged_in = True` and your `username`.
  - All other pages become accessible in the sidebar.
4. If you log out, your session is cleared and you’re returned to the Login page.

No page other than **Login** is accessible unless you are logged in.

---

## 5. How the Application Works

### 5.1 Navigation and Pages

The sidebar contains these pages:

- **Login** – authenticate before using the app
- **Dashboard** – high-level monthly view with charts
- **Record Expense** – add new expense entries
- **Record Revenue** – add new revenue entries
- **Expense Search** – search and filter expenses
- **Revenue Search** – search and filter revenues
- **Financial Summary** – income-statement style summaries
- **Reports** – generate and export CSV/Excel reports
- **Settings** – account settings (e.g. change password)

The app enforces login by checking `st.session_state.logged_in` before allowing navigation away from the Login page.

### 5.2 Recording Expenses

On **Record Expense** you capture:

- Date
- Supplier Name
- Supplier KRA PIN
- eTIMS Invoice Number
- Category (Rent, Salaries, Marketing, Utilities, Office Supplies, Travel, Technology, Consultancy, Other)
- Description
- Amount (KES) – **must be greater than zero**
- Payment Method (Cash, Bank Transfer, Mpesa, Card)
- Receipt Upload (JPG / PNG / PDF)

When you submit:

- The amount is validated to ensure it is **> 0**.
- The uploaded receipt is saved into `receipts/` with a standard name:
  - `expense_YYYY_MM_DD_<unique>.ext`
- The expense record is inserted into the `expenses` table, including a **relative file path** to the receipt file.

### 5.3 Recording Revenues

On **Record Revenue** you capture:

- Date
- Client Name
- Service Type
- Description
- Amount Received (KES) – validated to be **> 0**
- Payment Method (Cash, Bank Transfer, Mpesa, Card)
- Mpesa Reference
- Payment Receipt Upload (JPG / PNG / PDF)

On submission:

- The receipt is saved under `receipts/` using:
  - `revenue_YYYY_MM_DD_<unique>.ext`
- A new row is written into the `revenues` table, with a link to the stored receipt file.

### 5.4 Receipt Upload Handling

Allowed file types:

- **JPG**
- **PNG**
- **PDF**

Uploaded files are:

1. Stored in the `receipts/` folder.
2. Renamed to:
  `type_YYYY_MM_DD_<unique>.ext`  
   where `type` is `expense` or `revenue`, and `<unique>` ensures there are no collisions.
3. The database only stores the **relative path** to the saved file, so the app can reference it later.

---

## 6. Financial Dashboard

The **Dashboard** page provides a quick snapshot of current performance:

- **Total Revenue (Current Month)** – sum of all revenue entries this month
- **Total Expenses (Current Month)** – sum of all expense entries this month
- **Net Profit/Loss (Current Month)** – revenue minus expenses

All monetary amounts are displayed in **KES currency format**, e.g.:

- `KES 125,000.00`

### 6.1 Charts (Plotly)

The dashboard includes interactive Plotly charts:

- **Expense Breakdown by Category (Pie Chart)**  
Shows where money is going across categories like Rent, Salaries, Marketing, etc.
- **Revenue vs Expenses by Month (Bar Chart)**  
Groups revenue and expenses per month (e.g. 2026‑01, 2026‑02, …).
- **Cashflow Trend (Line Chart)**  
Plots **Net Cashflow = Revenue − Expenses** per month, to visualise trends.

These charts are powered by **Pandas group-by** operations and rendered with **Plotly Express**.

---

## 7. Financial Summary (Income Statement Style)

The **Financial Summary** page acts like a simple **income statement** for a selected period.

You can filter by:

- **Month** – choose a year and month
- **Year** – choose a full year
- **Custom Date Range** – specify any start and end dates

For the chosen period, the system calculates:

- **Total Revenue**
- **Total Expenses**
- **Net Profit or Net Loss**

Additional views:

- **Expense Breakdown by Category** – pie chart of expenses in the period.
- **Monthly Profit Trend** – line chart showing net profit per month within the selected window.

All these calculations rely on **Pandas** to:

- Filter rows by date range
- Group by month or category
- Sum financial amounts

---

## 8. Search Pages

### 8.1 Expense Search

On **Expense Search**, you can filter expenses by:

- **Date Range** (start and end date)
- **Category** (one or multiple)
- **Supplier Name** (text search, case-insensitive)

Results are shown in a table with:

- Dates
- Supplier details
- eTIMS invoice numbers
- Categories and descriptions
- Amount in **KES** format
- Payment methods
- Paths to the associated receipt files

### 8.2 Revenue Search

On **Revenue Search**, you can filter revenues by:

- **Date Range**
- **Client Name** (text search, case-insensitive)
- **Payment Method** (one or multiple)

The results table displays:

- Dates
- Client names and service types
- Descriptions
- Amounts in **KES** format
- Payment methods
- Mpesa references
- Receipt file paths

---

## 9. Reports & Exports

The **Reports** page generates the following report types:

- **Expense Report**
- **Revenue Report**
- **Monthly Profit and Loss Report**
- **Financial Summary Report**

You can choose:

- A **date range** filter.
- An **export format**:
  - **Excel (`.xlsx`)**
  - **CSV (`.csv`)**

When you click **Export**:

1. The app builds a Pandas `DataFrame` for the chosen report and date range.
2. It saves the file into the `exports/` directory with a timestamped name, e.g.:
  - `expense_report_20260307_102030.csv`
3. Streamlit shows a **Download** button so you can immediately save the file to your machine.

These exports are designed to be **KRA-friendly**, giving clear, structured data suitable for audits or further analysis.

---

## 10. How Data Is Stored Locally

- All structured data is stored in:
  - `arckae_finance.db` (SQLite file)
- All binary files (receipts, invoices, etc.) are stored in:
  - `receipts/`
- All generated reports are stored in:
  - `exports/`
- Automatic backups of the database are stored in:
  - `backups/`

Nothing leaves the local environment. This keeps your data private and under your control.

---

## 11. Running the Application (Developer / Local Use)

1. **Create & activate a virtual environment (recommended)**:
  ```bash
   python -m venv venv
   source venv/bin/activate  # Linux / macOS
   # On Windows:
   # venv\Scripts\activate
  ```
2. **Install dependencies**:
  ```bash
   pip install -r requirements.txt
  ```
3. **Run the Streamlit app**:
  ```bash
   streamlit run app.py
  ```
4. Open the provided URL in your browser (typically `http://localhost:8501`).

---

## 12. Building a Standalone Windows Executable

The app includes a `launcher.py` script so that you can package the system as a **single `.exe`** for Windows users.

### Step 1 – Install PyInstaller

```bash
pip install pyinstaller
```

If you already installed dependencies via `requirements.txt`, `pyinstaller` is already included.

### Step 2 – Build the Executable

From the project root:

```bash
pyinstaller --onefile --noconsole launcher.py
```

This command:

- Creates a standalone Windows executable that launches `launcher.py`.
- `launcher.py` simply starts Streamlit with:
  - `python -m streamlit run app.py`

### Step 3 – Locate and Rename the Executable

After PyInstaller finishes:

- Find the built executable at:
  - `dist/launcher.exe`
- Rename it to:
  - `ArcKAE-Finance.exe`

You can now **distribute `ArcKAE-Finance.exe`** to Windows users.  
When they double-click it:

1. A Python runtime inside the bundle starts.
2. Streamlit launches the app (`app.py`).
3. The user’s default browser opens the ArcKAE Finance interface.

No Python installation is required on the end user’s machine, as long as you ship the compiled `.exe`.

---

## 13. Developer Documentation

For a deeper explanation of:

- System architecture
- Database structure and migrations
- Authentication mechanisms
- Financial summary and reporting logic
- File upload and storage flow
- The full EXE packaging process

see `**DEVELOPER_GUIDE.md**`, which is written for developers, like me,  who are learning Python (also like me) and want to understand how everything fits together.