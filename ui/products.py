import customtkinter as ctk
from tkinter import messagebox
from services.catalog import products,categories,add_category,save_product,set_product_active
from services.approvals import submit_request
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,rtl_text,show_child_window,enable_rtl_entry,clean_entry

class Products(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); self.user=user; self.selected=None
        show_child_window(self, parent)
        self.title('المنتجات'); self.geometry('1000x650'); self.configure(fg_color=BG)
        label(self,'إدارة المنتجات',26,TEXT,True).pack(anchor='e',padx=22,pady=18)
        top=ctk.CTkFrame(self,fg_color='transparent'); top.pack(fill='x',padx=22)
        button(top,'+ منتج جديد',self.form,True).pack(side='right',padx=4)
        button(top,'+ تصنيف',self.new_category).pack(side='right',padx=4)
        self.listbox=ctk.CTkScrollableFrame(self,fg_color=PANEL); self.listbox.pack(fill='both',expand=True,padx=22,pady=15)
        bar=ctk.CTkFrame(self,fg_color='transparent'); bar.pack(fill='x',padx=22,pady=10)
        button(bar,'تعديل',self.edit).pack(side='right',padx=4); button(bar,'تفعيل / إيقاف',self.toggle).pack(side='right',padx=4)
        self.refresh()
    def refresh(self):
        for w in self.listbox.winfo_children(): w.destroy()
        self.rows={}
        for p in products(False):
            txt=f"{p['id']} | {p['name']} | {p['category']} | {p['price']:.2f} جنيه | {'متاح' if p['is_active'] else 'متوقف'}"
            b=ctk.CTkButton(self.listbox,text=rtl_text(txt),anchor='e',fg_color='#403327' if p['id']==self.selected else '#302923',command=lambda pid=p['id']:self.select(pid))
            b.pack(fill='x',pady=3); self.rows[p['id']]=p
    def notify(self, message):
        messagebox.showinfo('تم',message,parent=self)
    def new_category(self):
        w=ctk.CTkInputDialog(text='اسم التصنيف:',title='إضافة تصنيف'); name=w.get_input()
        if not name:return
        name=name.replace('\u200f','').replace('\u200e','').strip()
        try:
            if self.user['role']=='manager': add_category(name); self.notify('تمت إضافة التصنيف.')
            else: submit_request(self.user['id'],'إضافة تصنيف',{'operation':'add_category','name':name.strip()}); self.notify('تم إرسال طلب إضافة التصنيف للمدير.')
        except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)
    def form(self,p=None):
        w=ctk.CTkToplevel(self); w.geometry('420x420'); w.configure(fg_color=BG); w.grab_set()
        label(w,'بيانات المنتج',22,GOLD,True).pack(pady=20)
        name=enable_rtl_entry(ctk.CTkEntry(w,width=320,placeholder_text='اسم المنتج',justify='right')); name.pack(pady=8)
        price=ctk.CTkEntry(w,width=320,placeholder_text='السعر',justify='right'); price.pack(pady=8)
        cats=categories(); names=['بدون تصنيف']+[x['name'] for x in cats]
        cv=ctk.StringVar(value=p['category'] if p else names[0]); ctk.CTkOptionMenu(w,values=names,variable=cv,width=320).pack(pady=10)
        if p: name.insert(0,p['name']); price.insert(0,str(p['price']))
        def save():
            try:
                cid=next((x['id'] for x in cats if x['name']==cv.get()),None)
                payload={'operation':'edit_product' if p else 'add_product','id':p['id'] if p else None,'name':clean_entry(name),'price':float(price.get()),'category_id':cid}
                if not payload['name'] or payload['price']<0: raise ValueError('راجع اسم المنتج والسعر.')
                if self.user['role']=='manager': save_product(p['id'] if p else None,clean_entry(name),price.get(),cid); self.notify('تم حفظ المنتج.')
                else: submit_request(self.user['id'],'تعديل منتج' if p else 'إضافة منتج',payload); self.notify('تم إرسال طلب تعديل المنتج للمدير، ولن يتغير المنتج قبل الموافقة.')
                w.destroy(); self.refresh()
            except Exception as e: messagebox.showerror('خطأ',str(e),parent=w)
        button(w,'إرسال للموافقة' if self.user['role']!='manager' else 'حفظ',save,True,width=320).pack(pady=20)
    def select(self,pid): self.selected=pid; self.refresh()
    def edit(self):
        if self.selected:self.form(self.rows[self.selected])
        else:messagebox.showwarning('تنبيه','اختر منتجاً.',parent=self)
    def toggle(self):
        if not self.selected: messagebox.showwarning('تنبيه','اختر منتجاً.',parent=self); return
        p=self.rows[self.selected]; active=not bool(p['is_active'])
        try:
            if self.user['role']=='manager':set_product_active(p['id'],active);self.refresh()
            else:submit_request(self.user['id'],'تغيير حالة منتج',{'operation':'toggle_product','id':p['id'],'active':active});messagebox.showinfo('تم','تم إرسال طلب تغيير حالة المنتج للمدير.',parent=self)
        except Exception as e:messagebox.showerror('خطأ',str(e),parent=self)
