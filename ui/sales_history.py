import customtkinter as ctk
from tkinter import messagebox, simpledialog
from datetime import date
from services.sales import invoice_rows,cancel_invoice,delete_invoice
from services.users import all_users
from services.operations import rental_sales_rows
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,rtl_text,show_child_window

class SalesHistory(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); self.user=user; self.selected=None
        show_child_window(self, parent)
        self.title("سجل المبيعات"); self.geometry("1150x680"); self.configure(fg_color=BG)
        label(self,"سجل المبيعات",25,TEXT,True).pack(anchor="e",padx=20,pady=15)
        filters=ctk.CTkFrame(self,fg_color="transparent"); filters.pack(fill="x",padx=20)
        self.start=ctk.CTkEntry(filters,placeholder_text="من تاريخ YYYY-MM-DD",width=180); self.start.pack(side="right",padx=5)
        self.end=ctk.CTkEntry(filters,placeholder_text="إلى تاريخ YYYY-MM-DD",width=180); self.end.pack(side="right",padx=5)
        self.cashier=ctk.StringVar(value="الكل")
        self.user_map={"الكل":None}
        for u in all_users(): self.user_map[u["full_name"]]=u["id"]
        ctk.CTkOptionMenu(filters,values=list(self.user_map),variable=self.cashier,width=180).pack(side="right",padx=5)
        button(filters,"بحث",self.refresh,True).pack(side="right",padx=5)
        self.listbox=ctk.CTkScrollableFrame(self,fg_color=PANEL); self.listbox.pack(fill="both",expand=True,padx=20,pady=15)
        if user["role"]=="manager":
            actions=ctk.CTkFrame(self,fg_color="transparent")
            actions.pack(fill="x",padx=20,pady=(0,12))
            button(actions,"إلغاء الفاتورة المحددة",self.cancel).pack(side="right",padx=5)
            button(actions,"حذف الطلب نهائيًا",self.delete_selected).pack(side="right",padx=5)
        self.refresh()
    def refresh(self):
        for w in self.listbox.winfo_children(): w.destroy()
        cashier=self.user_map.get(self.cashier.get()) if self.user["role"]=="manager" else self.user["id"]
        rows=invoice_rows(self.start.get().strip() or None,self.end.get().strip() or None,cashier)
        if self.user["role"]!="manager": rows=[r for r in rows if r["user_id"]==self.user["id"]]
        self.rows={}
        for r in rows:
            status="ملغاة" if r["status"]=="cancelled" else "مكتملة"
            txt=f"مبيعة {r['invoice_number']} | الصالة {r.get('salon_name') or '—'} | الترابيزة {r.get('table_number') or '—'} | {r['created_at']} | {r['cashier_name']} | {r['items'] or ''} | خصم {r['discount']:.2f} | {r['total']:.2f} جنيه | {status}"
            b=ctk.CTkButton(self.listbox,text=rtl_text(txt),anchor="e",fg_color="#403327" if r["id"]==self.selected else "#302923",
                            command=lambda x=r["id"]:self.select(x))
            b.pack(fill="x",pady=3); self.rows[r["id"]]=r
        rental_rows = rental_sales_rows(self.start.get().strip() or None,self.end.get().strip() or None,cashier)
        for r in rental_rows:
            status={"out":"لم يرجع","partial":"رجع جزء","returned":"تم الإرجاع"}.get(r["status"],r["status"])
            txt=(f"تأجير #{r['id']} | {r['person_name']} | طاولات: {r['table_count']} | كراسي: {r['chair_count']} "
                 f"| {r['created_at']} | {r['cashier_name']} | الإجمالي {r['total']:.2f} جنيه "
                 f"| المدفوع {float(r['paid'] or 0)+float(r['extra_paid'] or 0):.2f} | {status}")
            ctk.CTkLabel(self.listbox,text=rtl_text(txt),anchor="e",justify="right",fg_color="#493b2c",corner_radius=7).pack(fill="x",pady=3,ipady=8)
    def select(self,i): self.selected=i; self.refresh()
    def cancel(self):
        if self.user["role"]!="manager": return
        if not self.selected: messagebox.showwarning("تنبيه","اختر فاتورة."); return
        reason=simpledialog.askstring("سبب الإلغاء","اكتب سبب إلغاء الفاتورة:",parent=self)
        if reason:
            try: cancel_invoice(self.selected,reason,self.user["id"]); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e),parent=self)

    def delete_selected(self):
        if self.user["role"] != "manager":
            messagebox.showerror("غير مسموح", "حذف الطلبات متاح للمدير فقط.", parent=self)
            return
        if not self.selected:
            messagebox.showwarning("تنبيه", "اختر طلبًا أولًا.", parent=self)
            return
        row = self.rows.get(self.selected)
        if not row:
            messagebox.showerror("خطأ", "لم يتم العثور على الطلب المحدد.", parent=self)
            return
        confirmed = messagebox.askyesno(
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف الطلب {row['invoice_number']} نهائيًا؟\n"
            "سيتم حذفه من سجل المبيعات والتقارير، ولا يمكن التراجع عن ذلك.",
            icon="warning", parent=self
        )
        if not confirmed:
            return
        reason = simpledialog.askstring(
            "سبب الحذف", "اكتب سبب حذف الطلب:", parent=self
        )
        if reason is None:
            return
        try:
            delete_invoice(self.selected, reason, self.user["id"])
            self.selected = None
            messagebox.showinfo("تم الحذف", "تم حذف الطلب وتسجيل العملية في سجل المراجعة.", parent=self)
            self.refresh()
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)
