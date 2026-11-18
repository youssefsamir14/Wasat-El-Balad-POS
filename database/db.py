import os, sys, sqlite3, shutil
from pathlib import Path
APP_DIR_NAME = "WasatElBaladPOS"
def get_data_dir():
    if sys.platform == "win32": root=Path(os.environ.get("LOCALAPPDATA",Path.home())); folder=root/APP_DIR_NAME
    else: folder=Path.home()/f".{APP_DIR_NAME.lower()}"
    folder.mkdir(parents=True,exist_ok=True); return folder
DB_PATH=get_data_dir()/"pos.db"
def get_connection():
    conn=sqlite3.connect(DB_PATH,timeout=20); conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON"); conn.execute("PRAGMA journal_mode=WAL"); return conn
def _backup_before_upgrade():
    """Create a consistent one-time safety copy before the 1.1.0 schema upgrade."""
    if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
        return
    try:
        src=sqlite3.connect(DB_PATH,timeout=20)
        tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required={'expenses','other_income','cafe_tables','rentals','rental_returns','approval_requests','salons'}
        cols={r[1] for r in src.execute('PRAGMA table_info(invoices)')} if 'invoices' in tables else set()
        draft_cols={r[1] for r in src.execute('PRAGMA table_info(invoice_drafts)')} if 'invoice_drafts' in tables else set()
        needs=not required.issubset(tables) or not {'table_number','discount_percent','salon_name'}.issubset(cols) or 'salon_name' not in draft_cols
        if needs:
            stamp=__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            target=DB_PATH.with_name(f'pos_backup_before_1_1_0_{stamp}.db')
            dst=sqlite3.connect(target)
            src.backup(dst)
            dst.close()
        src.close()
    except Exception:
        # Never prevent app startup solely because a backup could not be made.
        # The original database is not deleted or overwritten by this routine.
        raise

def initialize_database():
    _backup_before_upgrade()
    schema='''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE COLLATE NOCASE,full_name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('manager','cashier')),is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,is_active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,category_id INTEGER,name TEXT NOT NULL,price REAL NOT NULL CHECK(price>=0),is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(category_id) REFERENCES categories(id));
    CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_number TEXT NOT NULL UNIQUE,user_id INTEGER NOT NULL,subtotal REAL NOT NULL,discount REAL NOT NULL DEFAULT 0,total REAL NOT NULL,payment_method TEXT NOT NULL DEFAULT 'cash',status TEXT NOT NULL DEFAULT 'completed',cancel_reason TEXT,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS invoice_items(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_id INTEGER NOT NULL,product_id INTEGER,product_name TEXT NOT NULL,unit_price REAL NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0),line_total REAL NOT NULL,FOREIGN KEY(invoice_id) REFERENCES invoices(id),FOREIGN KEY(product_id) REFERENCES products(id));
    CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT NOT NULL,details TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS approval_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,action TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',decided_by INTEGER,decision_note TEXT,created_at TEXT NOT NULL,decided_at TEXT,FOREIGN KEY(user_id) REFERENCES users(id),FOREIGN KEY(decided_by) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,description TEXT,amount REAL NOT NULL CHECK(amount>=0),user_id INTEGER NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS other_income(id INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT NOT NULL,description TEXT,amount REAL NOT NULL CHECK(amount>=0),user_id INTEGER NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS cafe_tables(id INTEGER PRIMARY KEY AUTOINCREMENT,table_number INTEGER NOT NULL UNIQUE,is_active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS salons(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE COLLATE NOCASE,is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS rentals(id INTEGER PRIMARY KEY AUTOINCREMENT,person_name TEXT NOT NULL,phone TEXT,table_count INTEGER NOT NULL DEFAULT 0,chair_count INTEGER NOT NULL DEFAULT 0,table_price REAL NOT NULL DEFAULT 0,chair_price REAL NOT NULL DEFAULT 0,discount REAL NOT NULL DEFAULT 0,total REAL NOT NULL,paid REAL NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'out',notes TEXT,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,returned_at TEXT,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS rental_returns(id INTEGER PRIMARY KEY AUTOINCREMENT,rental_id INTEGER NOT NULL,table_returned INTEGER NOT NULL DEFAULT 0,chair_returned INTEGER NOT NULL DEFAULT 0,payment REAL NOT NULL DEFAULT 0,note TEXT,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(rental_id) REFERENCES rentals(id),FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS employee_wage_payments(id INTEGER PRIMARY KEY AUTOINCREMENT,employee_name TEXT NOT NULL,period TEXT,amount REAL NOT NULL CHECK(amount>0),notes TEXT,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS invoice_drafts(id INTEGER PRIMARY KEY AUTOINCREMENT,draft_number TEXT NOT NULL UNIQUE,cart_json TEXT NOT NULL,discount_percent REAL NOT NULL DEFAULT 0,table_number INTEGER, user_id INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS inventory_items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL COLLATE NOCASE UNIQUE,item_type TEXT NOT NULL CHECK(item_type IN ('ready','raw')),unit TEXT NOT NULL,quantity REAL NOT NULL DEFAULT 0 CHECK(quantity>=0),min_quantity REAL NOT NULL DEFAULT 0 CHECK(min_quantity>=0),avg_cost REAL NOT NULL DEFAULT 0 CHECK(avg_cost>=0),is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS inventory_movements(id INTEGER PRIMARY KEY AUTOINCREMENT,item_id INTEGER NOT NULL,movement_type TEXT NOT NULL,quantity REAL NOT NULL CHECK(quantity>=0),balance_after REAL NOT NULL CHECK(balance_after>=0),unit_cost REAL NOT NULL DEFAULT 0,notes TEXT,user_id INTEGER,created_at TEXT NOT NULL,FOREIGN KEY(item_id) REFERENCES inventory_items(id),FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS inventory_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,item_id INTEGER NOT NULL,request_type TEXT NOT NULL CHECK(request_type IN ('in','out')),quantity REAL NOT NULL CHECK(quantity>0),reason TEXT NOT NULL,requested_by INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),decided_by INTEGER,decision_note TEXT,created_at TEXT NOT NULL,decided_at TEXT,FOREIGN KEY(item_id) REFERENCES inventory_items(id),FOREIGN KEY(requested_by) REFERENCES users(id),FOREIGN KEY(decided_by) REFERENCES users(id));
    '''
    with get_connection() as c:
        c.executescript(schema)
        # Safe additive migrations: never drop or replace existing sales data.
        cols={r[1] for r in c.execute('PRAGMA table_info(invoices)')}
        for name,definition in [('cancel_reason','TEXT'),('table_number','INTEGER'),('discount_percent','REAL NOT NULL DEFAULT 0'),('salon_name','TEXT')]:
            if name not in cols: c.execute(f'ALTER TABLE invoices ADD COLUMN {name} {definition}')
        draft_cols={r[1] for r in c.execute('PRAGMA table_info(invoice_drafts)')}
        if 'salon_name' not in draft_cols: c.execute('ALTER TABLE invoice_drafts ADD COLUMN salon_name TEXT')
