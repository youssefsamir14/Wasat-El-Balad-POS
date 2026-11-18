import customtkinter as ctk
from tkinter import messagebox
from services.catalog import products,categories
from services.sales import create_invoice,invoice_details,save_invoice_draft,delete_invoice_draft,get_invoice_draft,complete_invoice_draft
from services.printing import print_receipt,print_temporary_receipt,print_kitchen_ticket
from services.operations import list_tables,list_salons
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,rtl_text,show_child_window,enable_rtl_entry,clean_entry

class Cashier(ctk.CTkToplevel):
    def __init__(self,parent,user,draft_id=None):
        super().__init__(parent); self.user=user; self.cart={}; self.draft_id=draft_id; self.title('الكاشير'); self.geometry('1200x720'); self.configure(fg_color=BG)
        show_child_window(self, parent)
        self.products=products(); self.all_categories=categories(); self.active_category=None; left=ctk.CTkFrame(self,fg_color=PANEL,width=650); left.pack(side='left',fill='both',expand=True,padx=15,pady=15)
        label(left,'اختار التصنيف ثم المنتج',24,GOLD,True).pack(anchor='e',padx=15,pady=(15,8))
        self.category_bar=ctk.CTkScrollableFrame(left,height=55,orientation='horizontal',fg_color='transparent'); self.category_bar.pack(fill='x',padx=10)
        self.grid=ctk.CTkScrollableFrame(left,fg_color='transparent'); self.grid.pack(fill='both',expand=True,padx=10,pady=10)
        self.render_categories(); self.render_products()
        right=ctk.CTkFrame(self,fg_color=PANEL,width=430); right.pack(side='right',fill='y',padx=15,pady=15); right.pack_propagate(False)
        label(right,'الفاتورة الحالية',23,TEXT,True).pack(pady=12)
        self.salons=list_salons(); self.salon_names=['بدون صالة']+[x['name'] for x in self.salons]; self.salon=ctk.StringVar(value='بدون صالة')
        ctk.CTkOptionMenu(right,values=self.salon_names,variable=self.salon).pack(fill='x',padx=15,pady=(5,3))
        self.table=enable_rtl_entry(ctk.CTkEntry(right,placeholder_text='رقم الترابيزة (اختياري)',justify='right')); self.table.pack(fill='x',padx=15,pady=5)
        self.cart_view=ctk.CTkScrollableFrame(right,fg_color='#302923'); self.cart_view.pack(fill='both',expand=True,padx=12,pady=8)
        self.total_label=label(right,'الإجمالي: 0.00 جنيه',22,GOLD,True); self.total_label.pack(pady=8)
        self.discount=ctk.CTkEntry(right,placeholder_text='نسبة الخصم % (اختياري)',justify='right'); self.discount.pack(fill='x',padx=15,pady=5); self.discount.bind('<KeyRelease>',lambda _e:self.render_cart())
        self.payment=ctk.StringVar(value='cash'); ctk.CTkOptionMenu(right,values=['cash','card'],variable=self.payment).pack(pady=5)
        button(right,'حفظ الفاتورة المؤقتة',self.save_draft,height=38).pack(fill='x',padx=15,pady=5)
        button(right,'طباعة / معاينة الفاتورة المؤقتة',self.prebill,height=38).pack(fill='x',padx=15,pady=5)
        button(right,'طباعة مطبخ (بدون أسعار)',self.print_kitchen,height=40).pack(fill='x',padx=15,pady=5)
        label(right,'يمكنك إضافة وحذف الأصناف وتغيير الكميات والخصم قبل اعتماد البيع.',11,MUTED).pack(pady=(0,4))
        button(right,'إتمام البيع وحفظ الفاتورة',self.checkout,True,height=43).pack(fill='x',padx=15,pady=5)
        button(right,'تفريغ السلة',self.clear).pack(fill='x',padx=15,pady=(0,10));
        if draft_id: self.load_draft(draft_id)
        self.render_cart()
    def render_categories(self):
        for w in self.category_bar.winfo_children(): w.destroy()
        cats=[('الكل',None),('بدون تصنيف',-1)]+[(x['name'],int(x['id'])) for x in self.all_categories]
        for title,cid in cats:
            ctk.CTkButton(self.category_bar,text=rtl_text(title),width=110,height=38,
                fg_color=GOLD if cid==self.active_category else '#51483D',
                text_color='#1B1712' if cid==self.active_category else TEXT,
                command=lambda x=cid:self.choose_category(x)).pack(side='right',padx=4,pady=4)
    def choose_category(self,cid):
        self.active_category=cid; self.render_categories(); self.render_products()
    def render_products(self):
        for w in self.grid.winfo_children(): w.destroy()
        shown=[p for p in self.products if (self.active_category is None or (self.active_category == -1 and not p.get('category_id')) or (self.active_category != -1 and p.get('category_id') is not None and int(p.get('category_id')) == int(self.active_category)))]
        for i,p in enumerate(shown):
            ctk.CTkButton(self.grid,text=rtl_text(f"{p['name']}\n{p['price']:.2f} جنيه"),height=85,fg_color='#403327',hover_color='#60482E',command=lambda x=p:self.add(x)).grid(row=i//3,column=i%3,padx=7,pady=7,sticky='nsew')
        if not shown: label(self.grid,'لا توجد منتجات في هذا التصنيف.',16,MUTED).pack(pady=30)
    def add(self,p):
        if p['id'] in self.cart:self.cart[p['id']]['quantity']+=1
        else:self.cart[p['id']]={'id':p['id'],'name':p['name'],'price':p['price'],'quantity':1}
        self.render_cart()
    def render_cart(self):
        for w in self.cart_view.winfo_children():w.destroy()
        for pid,item in self.cart.items():
            row=ctk.CTkFrame(self.cart_view,fg_color='#403327');row.pack(fill='x',pady=3)
            label(row,f"{item['name']} × {item['quantity']} | {item['price']*item['quantity']:.2f}",14,TEXT).pack(side='right',padx=5,pady=8)
            ctk.CTkButton(row,text='−',width=28,command=lambda x=pid:self.change(x,-1)).pack(side='left',padx=2)
            ctk.CTkButton(row,text='+',width=28,command=lambda x=pid:self.change(x,1)).pack(side='left',padx=2)
            ctk.CTkButton(row,text=rtl_text('حذف'),width=48,fg_color='#704333',hover_color='#8A4B3A',command=lambda x=pid:self.remove_item(x)).pack(side='left',padx=4)
        sub=sum(x['price']*x['quantity'] for x in self.cart.values()); disc=self.get_discount(sub)
        self.total_label.configure(text=f'الإجمالي: {sub-disc:.2f} جنيه')
    def get_discount(self,subtotal):
        try: pct=float(self.discount.get() or 0)
        except ValueError: pct=0
        return subtotal*min(100,max(0,pct))/100
    def change(self,pid,n):
        self.cart[pid]['quantity']+=n
        if self.cart[pid]['quantity']<=0:del self.cart[pid]
        self.render_cart()
    def remove_item(self,pid):
        self.cart.pop(pid,None)
        self.render_cart()
    def clear(self):
        self.cart={};self.discount.delete(0,'end');self.render_cart()
    def selected_salon(self):
        value=(self.salon.get() or '').strip()
        return value if value and value!='بدون صالة' else None
    def table_number(self):
        value=clean_entry(self.table).strip()
        if not value or value=='بدون طاولة': return None
        number=int(value)
        if number <= 0: raise ValueError('رقم الترابيزة يجب أن يكون أكبر من صفر.')
        return number
    def load_draft(self,draft_id):
        draft=get_invoice_draft(draft_id)
        if not draft: messagebox.showerror('خطأ','المسودة غير موجودة.',parent=self); self.destroy(); return
        if draft['user_id'] != self.user['id'] and self.user['role'] != 'manager':
            messagebox.showerror('صلاحيات','لا يمكنك تعديل مسودة كاشير آخر.',parent=self); self.destroy(); return
        self.cart={x.get('id') if x.get('id') is not None else f"draft-{i}":dict(x) for i,x in enumerate(draft['cart'])}
        if draft.get('table_number') is not None: self.table.insert(0,str(draft['table_number']))
        if draft.get('salon_name') in self.salon_names: self.salon.set(draft['salon_name'])
        self.discount.insert(0,str(draft.get('discount_percent',0))); self.render_cart()
    def save_draft(self):
        if not self.cart: messagebox.showwarning('تنبيه','السلة فارغة.',parent=self); return
        try:
            pct=float(self.discount.get() or 0)
            draft_id=save_invoice_draft(list(self.cart.values()),pct,self.table_number(),self.user['id'],self.draft_id,self.selected_salon())
            self.draft_id=draft_id
            messagebox.showinfo('تم الحفظ',f'تم حفظ الفاتورة المؤقتة رقم {draft_id}. يمكنك فتحها وتعديلها لاحقًا من صفحة الفواتير المؤقتة.',parent=self)
        except Exception as e: messagebox.showerror('تعذر حفظ المسودة',str(e),parent=self)
    def prebill(self):
        if not self.cart:messagebox.showwarning('تنبيه','السلة فارغة.',parent=self);return
        sub=sum(x['price']*x['quantity'] for x in self.cart.values());disc=self.get_discount(sub)
        try:print_temporary_receipt(list(self.cart.values()),sub,disc,round(sub-disc,2),self.table_number(),self.selected_salon())
        except Exception as e:messagebox.showerror('خطأ الطباعة',str(e),parent=self)
    def print_kitchen(self):
        if not self.cart:
            messagebox.showwarning('تنبيه','السلة فارغة.',parent=self); return
        try:
            print_kitchen_ticket(list(self.cart.values()), self.table_number(), salon_name=self.selected_salon())
            messagebox.showinfo('تمت الطباعة','تم إرسال تذكرة التحضير إلى طابعة المطبخ بدون أسعار. لم يتم تسجيل عملية بيع.',parent=self)
        except Exception as e:
            messagebox.showerror('تعذر طباعة تذكرة المطبخ',str(e),parent=self)
    def checkout(self):
        if not self.cart:messagebox.showwarning('تنبيه','السلة فارغة.',parent=self);return
        try:
            sub=sum(x['price']*x['quantity'] for x in self.cart.values());pct=float(self.discount.get() or 0)
            if not 0<=pct<=100:raise ValueError('نسبة الخصم يجب أن تكون بين 0 و100.')
            disc=round(sub*pct/100,2)
            if self.draft_id:
                save_invoice_draft(list(self.cart.values()),pct,self.table_number(),self.user['id'],self.draft_id,self.selected_salon())
                inv=complete_invoice_draft(self.draft_id,self.user['id'],self.payment.get())
            else:
                inv=create_invoice(list(self.cart.values()),self.user['id'],self.payment.get(),disc,self.table_number(),pct,self.selected_salon())
            _,items=invoice_details(inv['id']); self.draft_id=None; self.clear()
            if messagebox.askyesno('تم البيع',f"تم حفظ الفاتورة {inv['number']}\nالإجمالي {inv['total']:.2f} جنيه\nهل تريد طباعة الإيصال؟",parent=self):
                try:print_receipt(inv,items)
                except Exception as e:messagebox.showerror('خطأ الطباعة',f'تم حفظ الفاتورة لكن تعذرت الطباعة: {e}',parent=self)
        except Exception as e:messagebox.showerror('تعذر إتمام البيع',str(e),parent=self)
