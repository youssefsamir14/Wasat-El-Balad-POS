import json
import customtkinter as ctk
from tkinter import messagebox
from services.approvals import pending_requests,decide_request
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,show_child_window

class Approvals(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); self.user=user; self.title('طلبات الموافقة'); self.geometry('1000x650'); self.configure(fg_color=BG)
        show_child_window(self, parent)
        label(self,'طلبات موافقة الكاشير',25,TEXT,True).pack(anchor='e',padx=20,pady=18)
        self.list=ctk.CTkScrollableFrame(self,fg_color=PANEL); self.list.pack(fill='both',expand=True,padx=20,pady=12)
        self.refresh()
    def refresh(self):
        for w in self.list.winfo_children():w.destroy()
        rows=pending_requests()
        if not rows:label(self.list,'لا توجد طلبات معلقة حالياً.',17,MUTED).pack(pady=30);return
        for r in rows:
            p=json.loads(r['payload'])
            details=f"{r['action']} | مقدم الطلب: {r['full_name']} | وقت الطلب: {r['created_at']}"
            if p.get('operation') in ('add_product','edit_product'):
                details+=f"\nالمنتج: {p.get('name')} | السعر: {p.get('price')} جنيه | التصنيف: {p.get('category_id') or 'بدون تصنيف'}"
            elif p.get('operation')=='add_category':details+=f"\nاسم التصنيف: {p.get('name')}"
            elif p.get('operation')=='toggle_product':details+=f"\nرقم المنتج: {p.get('id')} | الحالة الجديدة: {'متاح' if p.get('active') else 'متوقف'}"
            box=ctk.CTkFrame(self.list,fg_color='#302923');box.pack(fill='x',pady=6,padx=5)
            label(box,details,15,TEXT,True,justify='right').pack(anchor='e',padx=12,pady=10)
            actions=ctk.CTkFrame(box,fg_color='transparent');actions.pack(anchor='e',padx=8,pady=(0,8))
            button(actions,'موافقة',lambda x=r['id']:self.decide(x,True),True,width=100).pack(side='right',padx=4)
            button(actions,'رفض',lambda x=r['id']:self.decide(x,False),width=100).pack(side='right',padx=4)
    def decide(self,rid,approve):
        note=''
        if not approve:
            w=ctk.CTkInputDialog(text='سبب الرفض (اختياري):',title='رفض الطلب');note=w.get_input() or ''
            if not messagebox.askyesno('تأكيد','هل تريد رفض الطلب؟',parent=self):return
        else:
            if not messagebox.askyesno('تأكيد الموافقة','سيتم تنفيذ التعديل فوراً. هل توافق؟',parent=self):return
        try:decide_request(rid,self.user['id'],approve,note);self.refresh()
        except Exception as e:messagebox.showerror('خطأ',str(e),parent=self)
