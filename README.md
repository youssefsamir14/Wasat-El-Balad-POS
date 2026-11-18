# Wasat El Balad POS | ليالي وسط البلد

A Python desktop point-of-sale and cafe operations application for Windows. The interface is Arabic-first and uses SQLite for local, offline operation.

> **Repository note:** This repository is a cleaned source-code snapshot based on project version 1.3.2. It is provided for portfolio review and development. It has not been independently validated as a production release on every Windows device or printer model.

## Main capabilities in this source snapshot

- Arabic desktop UI built with CustomTkinter.
- Local SQLite database and additive schema initialization/migrations.
- Manager and cashier accounts with password hashing.
- Product and category management.
- Sales invoices, invoice history, and saved draft invoices.
- Manager approval-request workflow for supported operations.
- Salon/table information associated with cafe operations.
- Expenses, other income, rentals, and employee wage records.
- Inventory items, stock movements, and cashier stock requests.
- Excel reports using OpenPyXL.
- Customer receipt printing and ESC/POS network kitchen-ticket printing.

Features and permission coverage should be reviewed in the source before relying on them operationally. Do not assume every administrative action is approval-gated merely because an approval workflow exists.

## Requirements

- Windows 10/11 (64-bit recommended)
- Python 3.10 or newer
- Dependencies listed in `requirements.txt`

## Run from source (Windows)

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py main.py
```

## First launch and manager account

On first launch, the application creates a manager account with username `admin` and generates a **random one-time password**. The credentials are written locally to:

`%LOCALAPPDATA%\\WasatElBaladPOS\\initial_admin_credentials.txt`

Read this file on the computer where the app was first launched. Change the password after signing in, then delete the credentials file. The file is excluded from Git by `.gitignore`.

## Build a Windows executable

Run `build_exe.bat` from the project folder. The script installs the dependencies and PyInstaller, then builds an onedir package under `dist\\WasatElBaladPOS`. Distribute the **entire folder**, not only the EXE.

## Data and privacy

- The SQLite database is stored locally under `%LOCALAPPDATA%\\WasatElBaladPOS\\pos.db` on Windows.
- Never commit a real `pos.db`, backups, customer details, employee details, receipts, logs, credentials, or `.env` files.
- Back up the database before updating or testing a new build.
- The default kitchen-printer address in settings is an example/default configuration. Change it in the app to match your own network.

## Project structure

```text
WasatElBaladPOS/
├── database/       # SQLite connection and schema initialization
├── services/       # Authentication, sales, reports, printing, inventory, etc.
├── ui/             # Desktop interface screens
├── main.py         # Application entry point
├── config.py       # Application configuration
├── requirements.txt
└── build_exe.bat
```

## Development and testing

Before using this software in a live cafe, test login, role permissions, approval decisions, draft lifecycle, invoice totals, database backup/restore, Excel exports, and both receipt and kitchen printers on the target Windows machine. Use a separate test database; never test destructive changes against live sales data.

## License

No license has been assigned yet. All rights are reserved by the project author unless a license file is added. Do not assume this code is available for reuse or redistribution under an open-source license.
