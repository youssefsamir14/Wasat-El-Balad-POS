from database.db import get_connection

def categories():
    with get_connection() as c:
        return [dict(r) for r in c.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY name")]

def add_category(name):
    name=name.strip()
    if not name: raise ValueError("اكتب اسم التصنيف.")
    with get_connection() as c: c.execute("INSERT INTO categories(name) VALUES(?)",(name,))

def products(active_only=True):
    sql = """SELECT p.*, COALESCE(c.name,'بدون تصنيف') category
             FROM products p LEFT JOIN categories c ON c.id=p.category_id"""
    if active_only: sql += " WHERE p.is_active=1"
    sql += " ORDER BY p.name"
    with get_connection() as c: return [dict(r) for r in c.execute(sql)]

def save_product(pid, name, price, category_id):
    name=name.strip()
    if not name: raise ValueError("اسم المنتج مطلوب.")
    price=float(price)
    if price < 0: raise ValueError("السعر غير صحيح.")
    with get_connection() as c:
        if pid:
            c.execute("UPDATE products SET name=?,price=?,category_id=? WHERE id=?",
                      (name,price,category_id or None,pid))
        else:
            c.execute("INSERT INTO products(name,price,category_id) VALUES(?,?,?)",
                      (name,price,category_id or None))

def set_product_active(pid, active):
    with get_connection() as c:
        c.execute("UPDATE products SET is_active=? WHERE id=?",(int(active),pid))
