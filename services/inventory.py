from datetime import datetime
from database.db import get_connection

def _now(): return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')

def is_manager(user):
    return str(user.get('role','')).lower() == 'manager'

def list_items(active_only=False):
    sql='SELECT * FROM inventory_items' + (' WHERE is_active=1' if active_only else '') + ' ORDER BY item_type,name'
    with get_connection() as c: return [dict(r) for r in c.execute(sql)]

def add_item(name,item_type,unit,opening_qty=0,min_qty=0,purchase_cost=0,user_id=None):
    name=(name or '').strip(); unit=(unit or '').strip(); item_type=(item_type or '').strip()
    opening_qty=float(opening_qty); min_qty=float(min_qty); purchase_cost=float(purchase_cost)
    if not name or not unit or item_type not in ('ready','raw'): raise ValueError('أدخل اسم الصنف ونوعه ووحدة القياس.')
    if opening_qty<0 or min_qty<0 or purchase_cost<0: raise ValueError('الكميات والأسعار لا يمكن أن تكون سالبة.')
    with get_connection() as c:
        cur=c.execute('INSERT INTO inventory_items(name,item_type,unit,quantity,min_quantity,avg_cost,is_active,created_at) VALUES(?,?,?,?,?,?,1,?)',(name,item_type,unit,opening_qty,min_qty,purchase_cost,_now()))
        iid=cur.lastrowid
        if opening_qty:
            c.execute('INSERT INTO inventory_movements(item_id,movement_type,quantity,balance_after,unit_cost,notes,user_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(iid,'opening',opening_qty,opening_qty,purchase_cost,'رصيد افتتاحي',user_id,_now()))
        return iid

def _apply_movement(c,item_id,movement_type,qty,user_id,notes='',unit_cost=None):
    qty=float(qty)
    if qty<=0: raise ValueError('أدخل كمية أكبر من صفر.')
    item=c.execute('SELECT * FROM inventory_items WHERE id=? AND is_active=1',(item_id,)).fetchone()
    if not item: raise ValueError('الصنف غير موجود أو متوقف.')
    current=float(item['quantity'])
    if movement_type=='in':
        cost=float(unit_cost if unit_cost is not None else item['avg_cost'])
        if cost<0: raise ValueError('تكلفة الشراء غير صحيحة.')
        new=current+qty
        avg=((current*float(item['avg_cost']))+(qty*cost))/new if new else cost
        c.execute('UPDATE inventory_items SET quantity=?,avg_cost=? WHERE id=?',(new,avg,item_id))
    elif movement_type=='out':
        if qty>current: raise ValueError(f'الكمية غير كافية. المتاح: {current:g} {item["unit"]}')
        new=current-qty; cost=float(item['avg_cost'])
        c.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(new,item_id))
    elif movement_type=='adjust':
        new=qty; delta=new-current; cost=float(item['avg_cost'])
        c.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(new,item_id)); qty=abs(delta); movement_type='adjustment'
    else: raise ValueError('نوع الحركة غير معروف.')
    c.execute('INSERT INTO inventory_movements(item_id,movement_type,quantity,balance_after,unit_cost,notes,user_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(item_id,movement_type,qty,new,cost,notes,user_id,_now()))
    c.execute('INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)',(user_id,'INVENTORY_'+movement_type.upper(),f'item={item_id}; qty={qty}; balance={new}; {notes}'))

def stock_in(item_id,qty,unit_cost,user_id,notes=''):
    with get_connection() as c: _apply_movement(c,item_id,'in',qty,user_id,notes,unit_cost)

def stock_out(item_id,qty,user_id,notes=''):
    with get_connection() as c: _apply_movement(c,item_id,'out',qty,user_id,notes)

def adjust_stock(item_id,new_qty,user_id,notes=''):
    with get_connection() as c: _apply_movement(c,item_id,'adjust',new_qty,user_id,notes)

def create_request(item_id,request_type,qty,reason,user_id):
    qty=float(qty); reason=(reason or '').strip()
    if qty<=0 or not reason: raise ValueError('أدخل كمية وسبب الطلب.')
    if request_type not in ('in','out'): raise ValueError('نوع الطلب غير صحيح.')
    with get_connection() as c:
        item=c.execute('SELECT id FROM inventory_items WHERE id=? AND is_active=1',(item_id,)).fetchone()
        if not item: raise ValueError('الصنف غير موجود.')
        cur=c.execute("INSERT INTO inventory_requests(item_id,request_type,quantity,reason,requested_by,status,created_at) VALUES(?,?,?,?,?,'pending',?)",(item_id,request_type,qty,reason,user_id,_now()))
        c.execute('INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)',(user_id,'INVENTORY_REQUEST',f'request={cur.lastrowid}; item={item_id}; type={request_type}; qty={qty}'))
        return cur.lastrowid

def list_requests(status=None, user_id=None):
    sql='''SELECT r.*,i.name item_name,i.unit,u.full_name requester, d.full_name decider FROM inventory_requests r JOIN inventory_items i ON i.id=r.item_id JOIN users u ON u.id=r.requested_by LEFT JOIN users d ON d.id=r.decided_by'''
    args=[]
    filters=[]
    if status: filters.append('r.status=?'); args.append(status)
    if user_id is not None: filters.append('r.requested_by=?'); args.append(user_id)
    if filters: sql+=' WHERE '+' AND '.join(filters)
    sql+=' ORDER BY r.id DESC'
    with get_connection() as c: return [dict(x) for x in c.execute(sql,args)]

def decide_request(request_id,approve,manager_id,note=''):
    with get_connection() as c:
        r=c.execute("SELECT * FROM inventory_requests WHERE id=? AND status='pending'",(request_id,)).fetchone()
        if not r: raise ValueError('الطلب غير موجود أو تم اتخاذ قرار بشأنه بالفعل.')
        if approve:
            _apply_movement(c,r['item_id'],r['request_type'],r['quantity'],manager_id,'تنفيذ طلب كاشير: '+r['reason'])
        c.execute("UPDATE inventory_requests SET status=?,decided_by=?,decision_note=?,decided_at=? WHERE id=?",('approved' if approve else 'rejected',manager_id,note,_now(),request_id))
        c.execute('INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)',(manager_id,'INVENTORY_REQUEST_DECISION',f'request={request_id}; approved={bool(approve)}; {note}'))

def list_movements(limit=500):
    with get_connection() as c:
        return [dict(r) for r in c.execute('''SELECT m.*,i.name item_name,i.unit,u.full_name actor FROM inventory_movements m JOIN inventory_items i ON i.id=m.item_id LEFT JOIN users u ON u.id=m.user_id ORDER BY m.id DESC LIMIT ?''',(int(limit),))]

def export_inventory_excel(output_path=None):
    from datetime import datetime
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from database.db import get_data_dir
    items=list_items(); moves=list_movements(100000); requests=list_requests()
    wb=Workbook(); ws=wb.active; ws.title='أرصدة المخزون'; ws.sheet_view.rightToLeft=True
    ws.append(['الصنف','النوع','الوحدة','الكمية الحالية','حد التنبيه','متوسط تكلفة الوحدة','قيمة المخزون'])
    for x in items:
        ws.append([x['name'],'منتج جاهز' if x['item_type']=='ready' else 'خامة / استخدام داخلي',x['unit'],x['quantity'],x['min_quantity'],x['avg_cost'],x['quantity']*x['avg_cost']])
    mv=wb.create_sheet('حركة المخزون'); mv.sheet_view.rightToLeft=True
    mv.append(['التاريخ','الصنف','نوع الحركة','الكمية','الرصيد بعد الحركة','تكلفة الوحدة','المستخدم','ملاحظات'])
    names={'opening':'رصيد افتتاحي','in':'إضافة','out':'صرف','adjustment':'تسوية'}
    for x in moves: mv.append([x['created_at'],x['item_name'],names.get(x['movement_type'],x['movement_type']),x['quantity'],x['balance_after'],x['unit_cost'],x.get('actor') or '',x.get('notes') or ''])
    rq=wb.create_sheet('طلبات الكاشير'); rq.sheet_view.rightToLeft=True
    rq.append(['رقم الطلب','الصنف','النوع','الكمية','السبب','مقدم الطلب','الحالة','صاحب القرار','ملاحظات القرار','تاريخ الطلب','تاريخ القرار'])
    for x in requests: rq.append([x['id'],x['item_name'],'إضافة' if x['request_type']=='in' else 'صرف',x['quantity'],x['reason'],x['requester'],x['status'],x.get('decider') or '',x.get('decision_note') or '',x['created_at'],x.get('decided_at') or ''])
    for sh in wb.worksheets:
        sh.freeze_panes='A2'; sh.auto_filter.ref=sh.dimensions; sh.sheet_view.showGridLines=False
        for cell in sh[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='8A6334'); cell.alignment=Alignment(horizontal='center',wrap_text=True)
        for col in range(1,sh.max_column+1): sh.column_dimensions[get_column_letter(col)].width=min(34,max(14,max((len(str(sh.cell(r,col).value or '')) for r in range(1,sh.max_row+1)),default=14)+2))
    path=output_path or (get_data_dir()/f"تقرير_المخزون_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    wb.save(path)
    return str(path)
