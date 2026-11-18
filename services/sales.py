from datetime import datetime
from database.db import get_connection

def create_invoice(cart, user_id, payment_method="cash", discount=0, table_number=None, discount_percent=0, salon_name=None):
    if not cart: raise ValueError("الفاتورة فارغة.")
    subtotal = sum(float(x["price"])*int(x["quantity"]) for x in cart)
    discount = float(discount)
    if discount < 0 or discount > subtotal: raise ValueError("قيمة الخصم غير صحيحة.")
    total = round(subtotal-discount,2)
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as c:
        cur = c.execute(
            """INSERT INTO invoices(invoice_number,user_id,subtotal,discount,total,payment_method,status,created_at,table_number,discount_percent,salon_name)
               VALUES('PENDING',?,?,?,?,?,'completed',?,?,?,?)""",
            (user_id,subtotal,discount,total,payment_method,now,table_number,discount_percent,salon_name)
        )
        invoice_id=cur.lastrowid
        number=f"WB-{datetime.now().astimezone():%Y%m%d}-{invoice_id:05d}"
        c.execute("UPDATE invoices SET invoice_number=? WHERE id=?",(number,invoice_id))
        for item in cart:
            qty=int(item["quantity"]); price=float(item["price"])
            c.execute("""INSERT INTO invoice_items(invoice_id,product_id,product_name,unit_price,quantity,line_total)
                         VALUES(?,?,?,?,?,?)""",
                      (invoice_id,item.get("id"),item["name"],price,qty,round(price*qty,2)))
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (user_id,"CREATE_INVOICE",f"{number}; total={total:.2f}"))
    return {"id":invoice_id,"number":number,"subtotal":subtotal,"discount":discount,"total":total,"created_at":now}

def invoice_rows(start=None, end=None, cashier=None):
    sql="""SELECT i.*,u.full_name cashier_name,u.username,
           GROUP_CONCAT(ii.product_name || ' × ' || ii.quantity, '، ') items
           FROM invoices i JOIN users u ON u.id=i.user_id
           LEFT JOIN invoice_items ii ON ii.invoice_id=i.id WHERE 1=1"""
    args=[]
    if start: sql += " AND date(i.created_at)>=date(?)"; args.append(start)
    if end: sql += " AND date(i.created_at)<=date(?)"; args.append(end)
    if cashier: sql += " AND i.user_id=?"; args.append(cashier)
    sql += " GROUP BY i.id ORDER BY i.id DESC"
    with get_connection() as c: return [dict(r) for r in c.execute(sql,args)]

def cancel_invoice(invoice_id, reason, actor):
    if not reason.strip(): raise ValueError("اكتب سبب إلغاء الفاتورة.")
    with get_connection() as c:
        row=c.execute("SELECT invoice_number,status FROM invoices WHERE id=?",(invoice_id,)).fetchone()
        if not row: raise ValueError("الفاتورة غير موجودة.")
        if row["status"]=="cancelled": raise ValueError("الفاتورة ملغاة بالفعل.")
        c.execute("UPDATE invoices SET status='cancelled',cancel_reason=? WHERE id=?",(reason.strip(),invoice_id))
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (actor,"CANCEL_INVOICE",f"{row['invoice_number']}: {reason.strip()}"))

def invoice_details(invoice_id):
    with get_connection() as c:
        inv=c.execute("""SELECT i.*,u.full_name cashier_name FROM invoices i JOIN users u ON u.id=i.user_id
                         WHERE i.id=?""",(invoice_id,)).fetchone()
        items=c.execute("SELECT * FROM invoice_items WHERE invoice_id=?",(invoice_id,)).fetchall()
        return dict(inv) if inv else None, [dict(x) for x in items]

def daily_summary():
    today=datetime.now().strftime("%Y-%m-%d")
    with get_connection() as c:
        row=c.execute("""SELECT COUNT(*) count, COALESCE(SUM(total),0) total
                         FROM invoices WHERE date(created_at)=? AND status='completed'""",(today,)).fetchone()
        return dict(row)


def delete_invoice(invoice_id, reason, actor):
    """Permanently delete an invoice; only an active manager may do this."""
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("اكتب سبب حذف الطلب.")
    with get_connection() as c:
        manager = c.execute(
            "SELECT role, is_active FROM users WHERE id=?", (actor,)
        ).fetchone()
        if not manager or manager["role"] != "manager" or not manager["is_active"]:
            raise PermissionError("حذف الطلبات متاح للمدير النشط فقط.")

        row = c.execute(
            "SELECT invoice_number, total, status FROM invoices WHERE id=?",
            (invoice_id,)
        ).fetchone()
        if not row:
            raise ValueError("الطلب غير موجود أو تم حذفه بالفعل.")

        # Keep an audit record even though the invoice and its items are removed.
        c.execute(
            "INSERT INTO audit_logs(user_id, action, details) VALUES(?,?,?)",
            (actor, "DELETE_INVOICE",
             f"{row['invoice_number']}; total={row['total']:.2f}; "
             f"status={row['status']}; reason={reason}")
        )
        c.execute("DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        c.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))


# Persistent cashier drafts: drafts are deliberately excluded from all sales queries.
def save_invoice_draft(cart, discount_percent, table_number, user_id, draft_id=None, salon_name=None):
    import json
    if not cart: raise ValueError("الفاتورة المؤقتة فارغة.")
    pct=float(discount_percent)
    if not 0 <= pct <= 100: raise ValueError("نسبة الخصم يجب أن تكون بين 0 و100.")
    payload=[]
    for item in cart:
        qty=int(item.get("quantity",0)); price=float(item.get("price",0))
        if qty <= 0 or price < 0: raise ValueError("راجع أصناف الفاتورة وكمياتها وأسعارها.")
        payload.append({"id":item.get("id"),"name":str(item["name"]),"price":price,"quantity":qty})
    data=json.dumps(payload,ensure_ascii=False)
    now=datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as c:
        if draft_id:
            cur=c.execute("UPDATE invoice_drafts SET cart_json=?,discount_percent=?,table_number=?,salon_name=?,updated_at=? WHERE id=? AND user_id=?",(data,pct,table_number,salon_name,now,draft_id,user_id))
            if not cur.rowcount: raise ValueError("المسودة غير موجودة أو لا تملك صلاحية تعديلها.")
            return int(draft_id)
        import uuid
        number=f"DRAFT-{datetime.now().astimezone():%Y%m%d%H%M%S}-{user_id}-{uuid.uuid4().hex[:6]}"
        cur=c.execute("INSERT INTO invoice_drafts(draft_number,cart_json,discount_percent,table_number,salon_name,user_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(number,data,pct,table_number,salon_name,user_id,now,now))
        return cur.lastrowid

def list_invoice_drafts():
    import json
    with get_connection() as c:
        rows=c.execute("SELECT d.*,u.full_name cashier FROM invoice_drafts d JOIN users u ON u.id=d.user_id ORDER BY d.updated_at DESC,d.id DESC").fetchall()
    result=[]
    for row in rows:
        item=dict(row); item["cart"]=json.loads(item.pop("cart_json")); item["total"]=round(sum(x["price"]*x["quantity"] for x in item["cart"])*(1-item["discount_percent"]/100),2); result.append(item)
    return result

def get_invoice_draft(draft_id):
    import json
    with get_connection() as c: row=c.execute("SELECT * FROM invoice_drafts WHERE id=?",(draft_id,)).fetchone()
    if not row: return None
    result=dict(row); result["cart"]=json.loads(result.pop("cart_json")); return result

def delete_invoice_draft(draft_id, user_id=None):
    with get_connection() as c:
        if user_id is None: cur=c.execute("DELETE FROM invoice_drafts WHERE id=?",(draft_id,))
        else: cur=c.execute("DELETE FROM invoice_drafts WHERE id=? AND user_id=?",(draft_id,user_id))
        return cur.rowcount > 0

def complete_invoice_draft(draft_id, user_id, payment_method='cash'):
    """Atomically convert a saved draft into one completed invoice and remove the draft."""
    import json
    with get_connection() as c:
        draft=c.execute('SELECT * FROM invoice_drafts WHERE id=?',(draft_id,)).fetchone()
        if not draft: raise ValueError('المسودة غير موجودة أو تم اعتمادها بالفعل.')
        if int(draft['user_id']) != int(user_id):
            role=c.execute('SELECT role FROM users WHERE id=?',(user_id,)).fetchone()
            if not role or role['role']!='manager': raise PermissionError('لا تملك صلاحية اعتماد مسودة كاشير آخر.')
        cart=json.loads(draft['cart_json'])
        if not cart: raise ValueError('الفاتورة المؤقتة فارغة.')
        subtotal=sum(float(x['price'])*int(x['quantity']) for x in cart)
        pct=float(draft['discount_percent']); discount=round(subtotal*pct/100,2); total=round(subtotal-discount,2)
        now=datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
        cur=c.execute("INSERT INTO invoices(invoice_number,user_id,subtotal,discount,total,payment_method,status,created_at,table_number,discount_percent,salon_name) VALUES('PENDING',?,?,?,?,?,'completed',?,?,?,?)",(user_id,subtotal,discount,total,payment_method,now,draft['table_number'],pct,draft['salon_name']))
        invoice_id=cur.lastrowid
        number=f"WB-{datetime.now().astimezone():%Y%m%d}-{invoice_id:05d}"
        c.execute('UPDATE invoices SET invoice_number=? WHERE id=?',(number,invoice_id))
        for item in cart:
            c.execute('INSERT INTO invoice_items(invoice_id,product_id,product_name,unit_price,quantity,line_total) VALUES(?,?,?,?,?,?)',(invoice_id,item.get('id'),item['name'],float(item['price']),int(item['quantity']),round(float(item['price'])*int(item['quantity']),2)))
        c.execute('DELETE FROM invoice_drafts WHERE id=?',(draft_id,))
        c.execute('INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)',(user_id,'COMPLETE_INVOICE_DRAFT',f'{number}; draft={draft_id}; total={total:.2f}'))
        return {'id':invoice_id,'number':number,'subtotal':subtotal,'discount':discount,'total':total,'created_at':now}
