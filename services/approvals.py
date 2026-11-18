import json
from database.db import get_connection
from services.catalog import add_category, save_product, set_product_active


def submit_request(user_id, action, payload):
    with get_connection() as c:
        cur = c.execute("INSERT INTO approval_requests(user_id,action,payload,status,created_at) VALUES(?,?,?,'pending',CURRENT_TIMESTAMP)",
                        (user_id, action, json.dumps(payload, ensure_ascii=False)))
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (user_id, 'REQUEST_APPROVAL', f'{action}: request_id={cur.lastrowid}'))
        return cur.lastrowid


def pending_requests():
    with get_connection() as c:
        return [dict(r) for r in c.execute("""SELECT a.*,u.full_name FROM approval_requests a
            JOIN users u ON u.id=a.user_id WHERE a.status='pending' ORDER BY a.id DESC""").fetchall()]


def decide_request(request_id, manager_id, approve, note=''):
    with get_connection() as c:
        row = c.execute("SELECT * FROM approval_requests WHERE id=? AND status='pending'", (request_id,)).fetchone()
        if not row: raise ValueError('الطلب لم يعد معلقاً.')
        if approve:
            p = json.loads(row['payload'])
            op = p.get('operation')
            if op == 'add_category': add_category(p['name'])
            elif op == 'add_product': save_product(None, p['name'], p['price'], p.get('category_id'))
            elif op == 'edit_product': save_product(p['id'], p['name'], p['price'], p.get('category_id'))
            elif op == 'toggle_product': set_product_active(p['id'], bool(p['active']))
            else: raise ValueError('نوع الطلب غير معروف.')
            status='approved'
        else: status='rejected'
        c.execute("UPDATE approval_requests SET status=?,decided_by=?,decision_note=?,decided_at=CURRENT_TIMESTAMP WHERE id=?",
                  (status, manager_id, note, request_id))
        c.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
                  (manager_id, 'APPROVAL_'+status.upper(), f'request_id={request_id}; {note}'))


def pending_count():
    with get_connection() as c:
        return int(c.execute("SELECT COUNT(*) FROM approval_requests WHERE status='pending'").fetchone()[0])
