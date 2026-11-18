from database.db import get_connection
from services.auth import hash_password

def all_users():
    with get_connection() as c:
        return [dict(x) for x in c.execute(
            "SELECT id,username,full_name,role,is_active,created_at FROM users ORDER BY id"
        ).fetchall()]

def add_user(username, full_name, password, role, actor):
    username, full_name = username.strip(), full_name.strip()
    if not username or not full_name or not password: raise ValueError("كل الحقول مطلوبة.")
    if role not in ("manager","cashier"): raise ValueError("الصلاحية غير صحيحة.")
    if len(password) < 8: raise ValueError("كلمة المرور يجب ألا تقل عن 8 أحرف.")
    with get_connection() as c:
        try:
            cur = c.execute("INSERT INTO users(username,full_name,password_hash,role) VALUES(?,?,?,?)",
                            (username,full_name,hash_password(password),role))
        except Exception as e:
            if "UNIQUE" in str(e).upper(): raise ValueError("اسم المستخدم موجود بالفعل.")
            raise
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (actor,"ADD_USER",f"Added {username}"))

def edit_user(uid, username, full_name, role, actor):
    if not username.strip() or not full_name.strip(): raise ValueError("الاسم واسم المستخدم مطلوبان.")
    if role not in ("manager","cashier"): raise ValueError("الصلاحية غير صحيحة.")
    with get_connection() as c:
        try:
            c.execute("UPDATE users SET username=?,full_name=?,role=? WHERE id=?",
                      (username.strip(),full_name.strip(),role,uid))
        except Exception as e:
            if "UNIQUE" in str(e).upper(): raise ValueError("اسم المستخدم موجود بالفعل.")
            raise
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (actor,"EDIT_USER",f"Edited user id={uid}"))

def toggle_user(uid, active, actor):
    with get_connection() as c:
        target = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not target: raise ValueError("المستخدم غير موجود.")
        if uid == actor and not active: raise ValueError("لا يمكنك تعطيل حسابك الحالي.")
        if target["role"] == "manager" and not active:
            count = c.execute("SELECT COUNT(*) n FROM users WHERE role='manager' AND is_active=1").fetchone()["n"]
            if count <= 1: raise ValueError("لا يمكن تعطيل آخر مدير نشط.")
        c.execute("UPDATE users SET is_active=? WHERE id=?", (int(active),uid))
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (actor,"TOGGLE_USER",f"{target['username']} active={int(active)}"))

def change_password(uid, password, actor):
    if len(password) < 8: raise ValueError("كلمة المرور يجب ألا تقل عن 8 أحرف.")
    with get_connection() as c:
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password),uid))
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (actor,"CHANGE_PASSWORD",f"Changed password for user id={uid}"))
