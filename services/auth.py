import hashlib, hmac, os, secrets
from pathlib import Path
from database.db import get_connection, get_data_dir

def hash_password(password):
    salt = os.urandom(16)
    rounds = 310000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"

def verify_password(password, stored):
    try:
        algo, rounds, salt, expected = stored.split("$")
        if algo != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual.hex(), expected)
    except Exception:
        return False

def ensure_default_manager():
    """Ensure a default admin account exists without overwriting existing credentials.

    This intentionally checks for the admin username, not whether the users table
    is empty. A database may already contain cashier accounts and still need its
    first manager account.
    """
    with get_connection() as conn:
        admin = conn.execute(
            "SELECT id FROM users WHERE username = ? COLLATE NOCASE", ("admin",)
        ).fetchone()
        if admin is None:
            initial_password = secrets.token_urlsafe(18)
            conn.execute(
                "INSERT INTO users(username,full_name,password_hash,role,is_active) VALUES(?,?,?,?,1)",
                ("admin", "مدير النظام", hash_password(initial_password), "manager")
            )
            # Store the one-time bootstrap credential locally, never in source control.
            credential_file = get_data_dir() / "initial_admin_credentials.txt"
            if not credential_file.exists():
                credential_file.write_text(
                    "Initial manager account\nUsername: admin\nPassword: " + initial_password + "\n\n"
                    "Change this password after your first login, then delete this file.\n",
                    encoding="utf-8",
                )

def login(username, password):
    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1", (username.strip(),)
        ).fetchone()
        if user and verify_password(password, user["password_hash"]):
            conn.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                         (user["id"], "LOGIN", "Successful login"))
            return {k:user[k] for k in ("id","username","full_name","role")}
    return None
