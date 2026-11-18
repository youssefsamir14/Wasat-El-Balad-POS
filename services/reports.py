from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from database.db import get_connection, get_data_dir

DARK = "4A3020"
GOLD = "D6A24F"
LIGHT = "F7F0E5"
WHITE = "FFFFFF"


def _style_title(ws, cell_range, title):
    ws.merge_cells(cell_range)
    cell = ws[cell_range.split(":")[0]]
    cell.value = title
    cell.font = Font(name="Arial", size=16, bold=True, color=WHITE)
    cell.fill = PatternFill("solid", fgColor=DARK)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[cell.row].height = 30


def _style_header(ws, row_num):
    for cell in ws[row_num]:
        if cell.value is not None:
            cell.font = Font(name="Arial", bold=True, color=WHITE)
            cell.fill = PatternFill("solid", fgColor=GOLD)
            cell.alignment = Alignment(horizontal="center", vertical="center", readingOrder=2, wrap_text=True)
    ws.row_dimensions[row_num].height = 28


def _finish_sheet(ws, widths=None, filter_from=None):
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = f"A{filter_from + 1}" if filter_from else None
    if filter_from is not None and ws.max_row >= filter_from:
        ws.auto_filter.ref = f"A{filter_from}:{get_column_letter(ws.max_column)}{ws.max_row}"
    if widths:
        for col, width in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                if cell.alignment.horizontal != "center":
                    cell.alignment = Alignment(horizontal="right", vertical="center", readingOrder=2, wrap_text=True)
                if cell.row > 1 and cell.row % 2 == 0 and cell.fill.fill_type is None:
                    cell.fill = PatternFill("solid", fgColor=LIGHT)
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_view.showGridLines = False


def _money(cell):
    cell.number_format = '#,##0.00 "جنيه"'


def _parse_sale_datetime(value):
    """Treat legacy naive timestamps as Cairo local time and return an aware datetime."""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value))
    # Use the Windows/system local timezone configured by the user.
    # Naive timestamps from older app versions are already stored as local wall time.
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.replace(tzinfo=None)  # Excel stores local wall-clock time; header states Cairo time.


def export_monthly_workbook(output_path=None):
    now = datetime.now().astimezone()
    with get_connection() as c:
        invoices = c.execute("""SELECT i.invoice_number,i.created_at,u.full_name cashier,
            i.subtotal,i.discount,i.total,i.payment_method,i.status,i.cancel_reason,
            GROUP_CONCAT(ii.product_name || ' × ' || ii.quantity, '، ') items
            FROM invoices i JOIN users u ON u.id=i.user_id
            LEFT JOIN invoice_items ii ON ii.invoice_id=i.id
            GROUP BY i.id ORDER BY i.created_at""").fetchall()

        # One row per sold product per invoice, preserving the exact sale date/time
        # and cashier. Discounts are allocated proportionally to line totals.
        cashier_product_rows = c.execute("""SELECT i.invoice_number, i.created_at,
            u.full_name cashier, ii.product_name, ii.quantity, ii.unit_price,
            ii.line_total,
            CASE WHEN i.subtotal > 0 THEN ii.line_total * (i.total / i.subtotal) ELSE 0 END net_amount
            FROM invoice_items ii JOIN invoices i ON i.id=ii.invoice_id
            JOIN users u ON u.id=i.user_id
            WHERE i.status='completed'
            ORDER BY i.created_at DESC, i.id DESC, ii.id""").fetchall()
        # Load operational ledgers early for the workbook summary.
        expense_rows = c.execute("SELECT e.created_at,e.category,e.description,e.amount,u.full_name FROM expenses e JOIN users u ON u.id=e.user_id ORDER BY e.created_at").fetchall()
        income_rows = c.execute("SELECT i.created_at,i.source,i.description,i.amount,u.full_name FROM other_income i JOIN users u ON u.id=i.user_id ORDER BY i.created_at").fetchall()
        rental_rows = c.execute("SELECT r.*,u.full_name FROM rentals r JOIN users u ON u.id=r.user_id ORDER BY r.created_at").fetchall()
        return_rows = c.execute("SELECT rr.*,u.full_name FROM rental_returns rr JOIN users u ON u.id=rr.user_id ORDER BY rr.created_at").fetchall()
        wage_rows = c.execute("SELECT p.created_at,p.employee_name,p.period,p.amount,p.notes,u.full_name FROM employee_wage_payments p JOIN users u ON u.id=p.user_id ORDER BY p.created_at").fetchall()

    completed = [r for r in invoices if r["status"] == "completed"]
    cancelled = [r for r in invoices if r["status"] == "cancelled"]
    month_totals = {}
    cashier_totals = {}
    for r in completed:
        month = r["created_at"][:7]
        m = month_totals.setdefault(month, {"count": 0, "total": 0.0})
        m["count"] += 1
        m["total"] += float(r["total"] or 0)
        key = (month, r["cashier"])
        cashier_totals[key] = cashier_totals.get(key, 0.0) + float(r["total"] or 0)

    wb = Workbook()
    dash = wb.active
    dash.title = "ملخص"
    _style_title(dash, "A1:D1", "تقرير مبيعات ليالي وسط البلد")
    dash.append(["تاريخ التصدير", now.strftime("%Y-%m-%d %H:%M"), "", ""])
    dash.append(["إجمالي الفواتير المكتملة", len(completed), "", ""])
    dash.append(["إجمالي الفواتير الملغاة", len(cancelled), "", ""])
    dash.append(["إجمالي المبيعات بعد الخصم - كل الفترات", round(sum(float(r["total"] or 0) for r in completed), 2), "جنيه", ""])
    current_month = now.strftime("%Y-%m")
    current_month_rows = [r for r in completed if r["created_at"][:7] == current_month]
    dash.append([f"مبيعات الشهر الحالي ({current_month})", round(sum(float(r["total"] or 0) for r in current_month_rows), 2), "جنيه", ""])
    dash.append(["عدد فواتير الشهر الحالي", len(current_month_rows), "", ""])
    rental_contract_total = sum(float(r["total"] or 0) for r in rental_rows)
    rental_collected_total = sum(float(r["paid"] or 0) for r in rental_rows)
    dash.append(["إجمالي قيمة تأجير الطاولات والكراسي", round(rental_contract_total,2), "جنيه", ""])
    dash.append(["إجمالي المبالغ المحصلة من التأجير", round(rental_collected_total,2), "جنيه", ""])
    dash.append(["إيرادات أخرى مسجلة", round(sum(float(r["amount"] or 0) for r in income_rows),2), "جنيه", ""])
    dash.append(["إجمالي أجور الموظفين المدفوعة", round(sum(float(r["amount"] or 0) for r in wage_rows),2), "جنيه", "مشمولة بالفعل ضمن المصروفات؛ لا تُخصم مرة ثانية"])
    dash.append([])

    dash.append(["ملخص المبيعات حسب الشهر", "عدد الفواتير", "إجمالي المبيعات بعد الخصم", ""])
    _style_header(dash, 8)
    for month, data in sorted(month_totals.items()):
        dash.append([month, data["count"], round(data["total"], 2), "جنيه"])
    monthly_end = dash.max_row
    dash.append([])

    dash.append([f"مبيعات كل كاشير خلال الشهر الحالي ({current_month})", "عدد الفواتير", "إجمالي المبيعات", ""])
    _style_header(dash, dash.max_row)
    current_cashiers = {}
    for r in current_month_rows:
        name = r["cashier"]
        entry = current_cashiers.setdefault(name, {"count": 0, "total": 0.0})
        entry["count"] += 1
        entry["total"] += float(r["total"] or 0)
    for name, data in sorted(current_cashiers.items(), key=lambda x: x[1]["total"], reverse=True):
        dash.append([name, data["count"], round(data["total"], 2), "جنيه"])
    dash.append([])

    dash.append(["رقم الفاتورة", "تاريخ ووقت البيع (توقيت مصر)", "اسم الكاشير", "المنتج", "الكمية", "سعر الوحدة", "صافي قيمة البيع"])
    _style_header(dash, dash.max_row)
    product_detail_start = dash.max_row + 1
    for r in cashier_product_rows:
        sale_dt = _parse_sale_datetime(r["created_at"])
        dash.append([r["invoice_number"], sale_dt, r["cashier"], r["product_name"],
                     r["quantity"], r["unit_price"], round(r["net_amount"] or 0, 2)])
        dash.cell(dash.max_row, 2).number_format = 'dd/mm/yyyy hh:mm:ss'
        for col in (6, 7):
            _money(dash.cell(dash.max_row, col))
    for row in range(2, 7):
        _money(dash.cell(row, 2))
    for row in range(9, monthly_end + 1):
        _money(dash.cell(row, 3))
    dash.column_dimensions["A"].width = 38
    dash.column_dimensions["B"].width = 26
    dash.column_dimensions["C"].width = 30
    dash.column_dimensions["D"].width = 24
    dash.column_dimensions["E"].width = 16
    _finish_sheet(dash)

    headers = ["رقم الفاتورة", "التاريخ والوقت", "اسم الكاشير", "المنتجات", "الإجمالي قبل الخصم", "الخصم", "الصافي بعد الخصم", "طريقة الدفع", "الحالة", "سبب الإلغاء"]
    months = {}
    for r in invoices:
        month = r["created_at"][:7]
        months.setdefault(month, []).append(r)
    for month, rows in sorted(months.items()):
        ws = wb.create_sheet(month)
        _style_title(ws, "A1:J1", f"فواتير شهر {month} - ليالي وسط البلد")
        ws.append(headers)
        _style_header(ws, 2)
        for r in rows:
            ws.append([r["invoice_number"], _parse_sale_datetime(r["created_at"]), r["cashier"], r["items"] or "",
                       r["subtotal"], r["discount"], r["total"], r["payment_method"],
                       "ملغاة" if r["status"] == "cancelled" else "مكتملة", r["cancel_reason"] or ""])
        for row in range(3, ws.max_row + 1):
            ws.cell(row, 2).number_format = 'dd/mm/yyyy hh:mm:ss'
            for col in (5, 6, 7):
                _money(ws.cell(row, col))
        _finish_sheet(ws, [20, 20, 24, 42, 19, 15, 19, 16, 14, 30], filter_from=2)

    # Additional operating sheets: expenses, other income, rentals and product analytics.
    with get_connection() as c:
        expense_rows = c.execute("SELECT e.created_at,e.category,e.description,e.amount,u.full_name FROM expenses e JOIN users u ON u.id=e.user_id ORDER BY e.created_at").fetchall()
        income_rows = c.execute("SELECT i.created_at,i.source,i.description,i.amount,u.full_name FROM other_income i JOIN users u ON u.id=i.user_id ORDER BY i.created_at").fetchall()
        rental_rows = c.execute("SELECT r.*,u.full_name FROM rentals r JOIN users u ON u.id=r.user_id ORDER BY r.created_at").fetchall()
        return_rows = c.execute("SELECT rr.*,u.full_name FROM rental_returns rr JOIN users u ON u.id=rr.user_id ORDER BY rr.created_at").fetchall()
        rental_payment_rows = c.execute("SELECT r.id rental_id,r.person_name,r.created_at,(r.paid-COALESCE((SELECT SUM(rr.payment) FROM rental_returns rr WHERE rr.rental_id=r.id),0)) amount,u.full_name FROM rentals r JOIN users u ON u.id=r.user_id WHERE (r.paid-COALESCE((SELECT SUM(rr.payment) FROM rental_returns rr WHERE rr.rental_id=r.id),0))>0 ORDER BY r.created_at").fetchall()
        return_payment_rows = c.execute("SELECT rr.rental_id,r.person_name,rr.created_at,rr.payment amount,u.full_name FROM rental_returns rr JOIN rentals r ON r.id=rr.rental_id JOIN users u ON u.id=rr.user_id WHERE rr.payment>0 ORDER BY rr.created_at").fetchall()

    # Unified cash-income ledger: other income plus actual rental payments.
    ws = wb.create_sheet("الإيرادات")
    _style_title(ws, "A1:F1", "سجل الإيرادات والتحصيلات")
    ws.append(["التاريخ", "نوع الإيراد", "البيان", "رقم العملية", "المبلغ المحصل", "الموظف"]); _style_header(ws, 2)
    income_ledger = []
    for r in income_rows:
        income_ledger.append((_parse_sale_datetime(r["created_at"]), "إيراد آخر", f"{r['source']} - {r['description'] or ''}", "", float(r["amount"] or 0), r["full_name"]))
    for r in rental_payment_rows:
        income_ledger.append((_parse_sale_datetime(r["created_at"]), "تحصيل تأجير", f"تأجير طاولات وكراسي - {r['person_name']}", r["rental_id"], float(r["amount"] or 0), r["full_name"]))
    for r in return_payment_rows:
        income_ledger.append((_parse_sale_datetime(r["created_at"]), "دفعة تأجير إضافية", f"دفعة عند إرجاع التأجير - {r['person_name']}", r["rental_id"], float(r["amount"] or 0), r["full_name"]))
    for row in sorted(income_ledger, key=lambda x: x[0]):
        ws.append(list(row)); ws.cell(ws.max_row,1).number_format='dd/mm/yyyy hh:mm:ss'; _money(ws.cell(ws.max_row,5))
    _finish_sheet(ws,[22,24,42,16,20,24],filter_from=2)

    ws = wb.create_sheet("المصروفات")
    _style_title(ws, "A1:E1", "سجل مصروفات ليالي وسط البلد")
    ws.append(["التاريخ", "البند", "التفاصيل", "المبلغ", "الموظف"]); _style_header(ws, 2)
    for r in expense_rows: ws.append([_parse_sale_datetime(r["created_at"]),r["category"],r["description"],r["amount"],r["full_name"]])
    for rr in range(3,ws.max_row+1): ws.cell(rr,1).number_format='dd/mm/yyyy hh:mm:ss'; _money(ws.cell(rr,4))
    _finish_sheet(ws,[22,22,36,18,24],filter_from=2)

    ws = wb.create_sheet("إيرادات أخرى")
    _style_title(ws, "A1:E1", "سجل الإيرادات الأخرى")
    ws.append(["التاريخ", "المصدر", "التفاصيل", "المبلغ", "الموظف"]); _style_header(ws, 2)
    for r in income_rows: ws.append([_parse_sale_datetime(r["created_at"]),r["source"],r["description"],r["amount"],r["full_name"]])
    for rr in range(3,ws.max_row+1): ws.cell(rr,1).number_format='dd/mm/yyyy hh:mm:ss'; _money(ws.cell(rr,4))
    _finish_sheet(ws,[22,22,36,18,24],filter_from=2)

    ws = wb.create_sheet("التأجير")
    _style_title(ws, "A1:M1", "سجل تأجير الطاولات والكراسي")
    ws.append(["رقم العملية","الاسم","التليفون","عدد الطاولات","عدد الكراسي","سعر الطاولة","سعر الكرسي","الخصم","الإجمالي","المدفوع","المتبقي","الحالة","الموظف"]); _style_header(ws,2)
    for r in rental_rows:
        ws.append([r["id"],r["person_name"],r["phone"],r["table_count"],r["chair_count"],r["table_price"],r["chair_price"],r["discount"],r["total"],r["paid"],r["total"]-r["paid"],{"out":"لم يرجع","partial":"رجع جزء","returned":"تم الإرجاع"}.get(r["status"],r["status"]),r["full_name"]])
    for rr in range(3,ws.max_row+1):
        for cc in range(6,12): _money(ws.cell(rr,cc))
    _finish_sheet(ws,[14,22,18,16,16,16,16,14,16,16,16,16,24],filter_from=2)

    # A separate movement log records each partial/full return and any extra payment.
    ws = wb.create_sheet("حركة مرتجعات التأجير")
    _style_title(ws, "A1:H1", "سجل إرجاع الطاولات والكراسي والدفعات")
    ws.append(["رقم التأجير", "اسم المستأجر", "الطاولات المرتجعة", "الكراسي المرتجعة", "دفعة إضافية", "ملاحظات", "الموظف المستلم", "تاريخ الإرجاع"])
    _style_header(ws, 2)
    for rr in return_rows:
        rental = next((x for x in rental_rows if x["id"] == rr["rental_id"]), None)
        ws.append([rr["rental_id"], rental["person_name"] if rental else "", rr["table_returned"], rr["chair_returned"], rr["payment"], rr["note"] or "", rr["full_name"], _parse_sale_datetime(rr["created_at"])])
        ws.cell(ws.max_row, 8).number_format = 'dd/mm/yyyy hh:mm:ss'
        _money(ws.cell(ws.max_row, 5))
    _finish_sheet(ws,[14,24,18,18,18,32,24,22],filter_from=2)

    ws = wb.create_sheet("تحليل المنتجات")
    _style_title(ws, "A1:C1", "تحليل مبيعات المنتجات")
    ws.append(["المنتج","الكمية المباعة","صافي المبيعات"]); _style_header(ws,2)
    for r in cashier_product_rows:
        pass
    product_totals = {}
    for r in cashier_product_rows:
        x=product_totals.setdefault(r["product_name"],{"qty":0,"revenue":0.0})
        x["qty"] += int(r["quantity"]); x["revenue"] += float(r["net_amount"] or 0)
    for name,x in sorted(product_totals.items(),key=lambda z:z[1]["qty"],reverse=True): ws.append([name,x["qty"],round(x["revenue"],2)])
    for rr in range(3,ws.max_row+1): _money(ws.cell(rr,3))
    _finish_sheet(ws,[38,20,24],filter_from=2)

    # Dedicated payroll detail sheet. Wage payments are already included in the
    # expenses sheet exactly once; this sheet is a breakdown, not extra income/expense.
    ws = wb.create_sheet("أجور الموظفين")
    _style_title(ws, "A1:F1", "سجل أجور الموظفين")
    ws.append(["التاريخ", "اسم الموظف", "الفترة", "المبلغ المدفوع", "ملاحظات", "المسجل"]); _style_header(ws, 2)
    for r in wage_rows:
        ws.append([_parse_sale_datetime(r["created_at"]),r["employee_name"],r["period"],r["amount"],r["notes"],r["full_name"]])
        ws.cell(ws.max_row,1).number_format='dd/mm/yyyy hh:mm:ss'; _money(ws.cell(ws.max_row,4))
    _finish_sheet(ws,[22,24,20,20,36,24],filter_from=2)

    # Keep every export: a new timestamped workbook is created instead of
    # silently overwriting the previous report with the same filename.
    report_path = output_path or (get_data_dir() / f"Wasat_El_Balad_Sales_{now:%Y%m%d_%H%M%S}.xlsx")
    wb.save(report_path)
    return report_path
