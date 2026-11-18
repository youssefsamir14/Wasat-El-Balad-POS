import customtkinter as ctk
from tkinter import messagebox
from ui.common import BG, PANEL, GOLD, TEXT, MUTED, button, label,show_child_window
from services.sales import list_invoice_drafts, delete_invoice_draft

class InvoiceDrafts(ctk.CTkToplevel):
    def __init__(self, parent, user):
        super().__init__(parent)
        show_child_window(self, parent)
        self.user=user
        self.title('الفواتير المؤقتة')
        self.geometry('900x650')
        self.configure(fg_color=BG)
        label(self, 'الفواتير المؤقتة المحفوظة', 24, GOLD, True).pack(pady=14)
        label(self, 'المسودات لا تدخل في المبيعات أو الإيرادات إلا بعد اعتماد البيع من شاشة الكاشير.', 13, MUTED).pack(pady=(0,8))
        self.rows=ctk.CTkScrollableFrame(self, fg_color=PANEL)
        self.rows.pack(fill='both', expand=True, padx=16, pady=10)
        button(self, 'تحديث القائمة', self.refresh, True, width=180).pack(pady=10)
        self.refresh()

    def refresh(self):
        for w in self.rows.winfo_children(): w.destroy()
        drafts=list_invoice_drafts()
        if self.user['role'] != 'manager':
            drafts=[d for d in drafts if d['user_id']==self.user['id']]
        if not drafts:
            label(self.rows, 'لا توجد فواتير مؤقتة محفوظة.', 16, MUTED).pack(pady=24)
            return
        for d in drafts:
            row=ctk.CTkFrame(self.rows, fg_color='#403327')
            row.pack(fill='x', padx=6, pady=5)
            info=f"مسودة #{d['id']} | {d['updated_at']} | الكاشير: {d['cashier']} | عدد الأصناف: {len(d['cart'])} | الإجمالي: {d['total']:.2f} جنيه | الصالة: {d.get('salon_name') or '—'} | الترابيزة: {d['table_number'] or 'بدون'}"
            label(row, info, 13, TEXT).pack(side='right', padx=10, pady=12)
            button(row, 'فتح وتعديل', lambda x=d['id']: self.edit(x), True, width=110).pack(side='left', padx=4, pady=6)
            button(row, 'حذف المسودة', lambda x=d['id']: self.remove(x), width=100).pack(side='left', padx=4, pady=6)

    def edit(self, draft_id):
        from ui.cashier import Cashier
        Cashier(self, self.user, draft_id=draft_id)
        self.refresh()

    def remove(self, draft_id):
        if not messagebox.askyesno('تأكيد', 'هل تريد حذف هذه الفاتورة المؤقتة؟', parent=self):
            return
        ok=delete_invoice_draft(draft_id, None if self.user['role']=='manager' else self.user['id'])
        if not ok:
            messagebox.showerror('تعذر الحذف', 'المسودة غير موجودة أو لا تملك صلاحية حذفها.', parent=self)
        self.refresh()
