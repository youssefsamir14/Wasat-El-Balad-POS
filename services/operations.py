from datetime import datetime, date
from database.db import get_connection

def now(): return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
def selected_datetime(value=None):
    if not value:
        return now()
    try:
        chosen = datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('صيغة التاريخ غير صحيحة.')
    return datetime.combine(chosen, datetime.now().astimezone().time().replace(tzinfo=None)).strftime('%Y-%m-%d %H:%M:%S')
def list_tables():
    with get_connection() as c: return [dict(r) for r in c.execute('SELECT * FROM cafe_tables ORDER BY table_number')]
def set_table_count(count):
    count=int(count)
    if not 1<=count<=300: raise ValueError('عدد الطاولات يجب أن يكون بين 1 و300.')
    with get_connection() as c:
        current={r['table_number']:r['id'] for r in c.execute('SELECT * FROM cafe_tables')}
        for n in range(1,count+1): c.execute('INSERT OR IGNORE INTO cafe_tables(table_number) VALUES(?)',(n,))
        # Do not delete numbered tables; deactivate excess ones to preserve history.
        c.execute('UPDATE cafe_tables SET is_active=CASE WHEN table_number<=? THEN 1 ELSE 0 END',(count,))
def add_expense(category,description,amount,user,transaction_date=None):
    amount=float(amount)
    if not category.strip() or amount<=0: raise ValueError('أدخل نوع المصروف ومبلغًا أكبر من صفر.')
    with get_connection() as c: c.execute('INSERT INTO expenses(category,description,amount,user_id,created_at) VALUES(?,?,?,?,?)',(category.strip(),description.strip(),amount,user,selected_datetime(transaction_date)))
def add_income(source,description,amount,user,transaction_date=None):
    amount=float(amount)
    if not source.strip() or amount<=0: raise ValueError('أدخل مصدر الإيراد ومبلغًا أكبر من صفر.')
    with get_connection() as c: c.execute('INSERT INTO other_income(source,description,amount,user_id,created_at) VALUES(?,?,?,?,?)',(source.strip(),description.strip(),amount,user,selected_datetime(transaction_date)))
def finance_summary():
    with get_connection() as c:
        e=c.execute('SELECT COALESCE(SUM(amount),0) FROM expenses').fetchone()[0]
        i=c.execute('SELECT COALESCE(SUM(amount),0) FROM other_income').fetchone()[0]
        s=c.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE status='completed'").fetchone()[0]
        return {'sales':s,'income':i,'expenses':e,'net':s+i-e}
def product_analysis():
    with get_connection() as c: return [dict(r) for r in c.execute("""SELECT ii.product_name,SUM(ii.quantity) quantity,ROUND(SUM(ii.line_total*(CASE WHEN i.subtotal>0 THEN i.total/i.subtotal ELSE 0 END)),2) revenue FROM invoice_items ii JOIN invoices i ON i.id=ii.invoice_id WHERE i.status='completed' GROUP BY ii.product_name ORDER BY quantity DESC""")]
def create_rental(data,user):
    name=data['person_name'].strip(); tc=int(data['table_count']); cc=int(data['chair_count']); tp=float(data['table_price']); cp=float(data['chair_price']); disc=float(data.get('discount',0)); paid=float(data.get('paid',0))
    subtotal=tc*tp+cc*cp; total=round(subtotal-disc,2)
    if not name or tc<0 or cc<0 or tc+cc==0 or tp<0 or cp<0 or disc<0 or disc>subtotal or paid<0 or paid>total: raise ValueError('راجع الاسم والأعداد والأسعار والخصم والمبلغ المدفوع.')
    with get_connection() as c:
        cur=c.execute('INSERT INTO rentals(person_name,phone,table_count,chair_count,table_price,chair_price,discount,total,paid,notes,user_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(name,data.get('phone',''),tc,cc,tp,cp,disc,total,paid,data.get('notes',''),user,now()))
        rid=cur.lastrowid; c.execute('INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)',(user,'CREATE_RENTAL',f'Rental #{rid}; {name}; total={total:.2f}; paid={paid:.2f}'))
    return rid
def rentals():
    with get_connection() as c: return [dict(r) for r in c.execute("""SELECT r.*,u.full_name cashier,(r.total-r.paid) remaining,COALESCE((SELECT SUM(table_returned) FROM rental_returns x WHERE x.rental_id=r.id),0) returned_tables,COALESCE((SELECT SUM(chair_returned) FROM rental_returns x WHERE x.rental_id=r.id),0) returned_chairs FROM rentals r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC""")] 
def return_rental(rid,tables,chairs,payment,note,user):
    tables=int(tables); chairs=int(chairs); payment=float(payment)
    with get_connection() as c:
        r=c.execute('SELECT * FROM rentals WHERE id=?',(rid,)).fetchone()
        if not r: raise ValueError('عملية التأجير غير موجودة.')
        prev=c.execute('SELECT COALESCE(SUM(table_returned),0) t,COALESCE(SUM(chair_returned),0) ch FROM rental_returns WHERE rental_id=?',(rid,)).fetchone()
        if tables<0 or chairs<0 or tables+prev['t']>r['table_count'] or chairs+prev['ch']>r['chair_count'] or payment<0 or payment>r['total']-r['paid']: raise ValueError('عدد المرتجعات أو المبلغ غير صحيح.')
        c.execute('INSERT INTO rental_returns(rental_id,table_returned,chair_returned,payment,note,user_id,created_at) VALUES(?,?,?,?,?,?,?)',(rid,tables,chairs,payment,note,user,now()))
        paid=r['paid']+payment; returned_t=prev['t']+tables; returned_c=prev['ch']+chairs
        status='returned' if returned_t==r['table_count'] and returned_c==r['chair_count'] else ('partial' if returned_t or returned_c else 'out')
        c.execute('UPDATE rentals SET paid=?,status=?,returned_at=? WHERE id=?',(paid,status,now() if status=='returned' else None,rid))
        c.execute('INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)',(user,'RENTAL_RETURN',f'#{rid}; tables={tables}; chairs={chairs}; payment={payment:.2f}; status={status}'))


def rental_sales_rows(start=None, end=None, cashier=None):
    """Rental contracts and payments for the unified sales register."""
    sql = """SELECT r.id, r.person_name, r.phone, r.table_count, r.chair_count,
        r.table_price, r.chair_price, r.discount, r.total, r.paid, r.status,
        r.created_at, u.full_name cashier_name,
        COALESCE((SELECT SUM(payment) FROM rental_returns rr WHERE rr.rental_id=r.id),0) extra_paid
        FROM rentals r JOIN users u ON u.id=r.user_id WHERE 1=1"""
    args=[]
    if start: sql += " AND date(r.created_at)>=date(?)"; args.append(start)
    if end: sql += " AND date(r.created_at)<=date(?)"; args.append(end)
    if cashier: sql += " AND r.user_id=?"; args.append(cashier)
    sql += " ORDER BY r.id DESC"
    with get_connection() as c: return [dict(x) for x in c.execute(sql,args)]


def add_employee_wage(employee_name, period, amount, notes, user, transaction_date=None):
    """Record a wage payment once in payroll ledger and once as an operating expense."""
    employee_name=(employee_name or '').strip(); period=(period or '').strip(); notes=(notes or '').strip(); amount=float(amount)
    if not employee_name or amount<=0: raise ValueError('أدخل اسم الموظف ومبلغًا أكبر من صفر.')
    payment_time=selected_datetime(transaction_date)
    with get_connection() as c:
        cur=c.execute('INSERT INTO employee_wage_payments(employee_name,period,amount,notes,user_id,created_at) VALUES(?,?,?,?,?,?)',(employee_name,period,amount,notes,user,payment_time))
        c.execute('INSERT INTO expenses(category,description,amount,user_id,created_at) VALUES(?,?,?,?,?)',('أجور الموظفين',f'{employee_name} | {period} | {notes}'.strip(' |'),amount,user,payment_time))
        c.execute('INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)',(user,'EMPLOYEE_WAGE_PAYMENT',f'{employee_name}; period={period}; amount={amount:.2f}'))
        return cur.lastrowid

def employee_wage_payments():
    with get_connection() as c:
        return [dict(r) for r in c.execute('SELECT p.*,u.full_name recorded_by FROM employee_wage_payments p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC')]


def finance_transactions(kind, limit=200):
    """Return recent expense or other-income records for the finance screens."""
    if kind == 'expenses':
        sql = "SELECT e.id, e.category AS title, e.description, e.amount, e.created_at, u.full_name AS recorded_by FROM expenses e JOIN users u ON u.id=e.user_id WHERE COALESCE(e.category,'') <> 'أجور الموظفين' ORDER BY e.id DESC LIMIT ?"
    elif kind == 'income':
        sql = "SELECT i.id, i.source AS title, i.description, i.amount, i.created_at, u.full_name AS recorded_by FROM other_income i JOIN users u ON u.id=i.user_id ORDER BY i.id DESC LIMIT ?"
    else:
        raise ValueError('نوع سجل غير معروف.')
    with get_connection() as c:
        return [dict(r) for r in c.execute(sql, (int(limit),))]


def employee_monthly_wage_summary(employee_name, year_month):
    """Aggregate actual wage payments for one employee in YYYY-MM month."""
    employee_name=(employee_name or '').strip()
    if not employee_name:
        raise ValueError('اكتب اسم الموظف.')
    try:
        datetime.strptime(year_month, '%Y-%m')
    except ValueError:
        raise ValueError('اختار شهرًا صحيحًا.')
    with get_connection() as c:
        rows=[dict(r) for r in c.execute(
            "SELECT id, employee_name, period, amount, notes, created_at FROM employee_wage_payments "
            "WHERE employee_name=? AND substr(created_at,1,7)=? ORDER BY created_at, id",
            (employee_name, year_month))]
    return {'employee_name':employee_name, 'month':year_month,
            'payments':rows, 'payment_count':len(rows),
            'total_received':round(sum(float(r['amount']) for r in rows),2)}


def list_salons(active_only=True):
    with get_connection() as c:
        sql='SELECT * FROM salons' + (' WHERE is_active=1' if active_only else '') + ' ORDER BY name COLLATE NOCASE'
        return [dict(r) for r in c.execute(sql)]

def add_salon(name):
    name=(name or '').strip()
    if not name: raise ValueError('اكتب اسم الصالة.')
    if len(name)>60: raise ValueError('اسم الصالة طويل جدًا.')
    with get_connection() as c:
        try: cur=c.execute('INSERT INTO salons(name,is_active) VALUES(?,1)',(name,))
        except Exception as e: raise ValueError('اسم الصالة موجود بالفعل.') from e
        return cur.lastrowid

def set_salon_active(salon_id, active):
    with get_connection() as c:
        cur=c.execute('UPDATE salons SET is_active=? WHERE id=?',(1 if active else 0,int(salon_id)))
        if not cur.rowcount: raise ValueError('الصالة غير موجودة.')


def delete_salon(salon_id):
    """Delete a salon from the selectable salon list. Historical invoices keep their saved salon_name snapshot."""
    with get_connection() as c:
        cur=c.execute('DELETE FROM salons WHERE id=?',(int(salon_id),))
        if not cur.rowcount:
            raise ValueError('الصالة غير موجودة.')
        return True
