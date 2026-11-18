import customtkinter as ctk
from tkinter import messagebox, filedialog
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,show_child_window,enable_rtl_entry,clean_entry
from services.inventory import list_items,add_item,stock_in,stock_out,create_request,list_requests,decide_request,list_movements,export_inventory_excel

class Inventory(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); self.user=user; self.selected=None; self.manager=user.get('role')=='manager'
        show_child_window(self,parent); self.title('إدارة المخازن'); self.geometry('1100x720'); self.configure(fg_color=BG)
        label(self,'إدارة المخازن',26,GOLD,True).pack(anchor='e',padx=20,pady=15)
        tabs=ctk.CTkTabview(self); tabs.pack(fill='both',expand=True,padx=18,pady=10)
        self.items_tab=tabs.add('الأصناف والكميات'); self.moves_tab=tabs.add('حركة المخزون'); self.requests_tab=tabs.add('طلبات الكاشير')
        self.items_list=ctk.CTkScrollableFrame(self.items_tab,fg_color=PANEL); self.items_list.pack(fill='both',expand=True,padx=8,pady=8)
        self.moves_list=ctk.CTkScrollableFrame(self.moves_tab,fg_color=PANEL) if self.manager else None
        if self.manager: self.moves_list.pack(fill='both',expand=True,padx=8,pady=8)
        self.requests_list=ctk.CTkScrollableFrame(self.requests_tab,fg_color=PANEL); self.requests_list.pack(fill='both',expand=True,padx=8,pady=8)
        bar=ctk.CTkFrame(self.items_tab,fg_color='transparent'); bar.pack(fill='x',padx=8,pady=8)
        if self.manager:
            button(bar,'إضافة صنف',self.add_item,True).pack(side='right',padx=4)
            button(bar,'إضافة كمية',self.in_stock).pack(side='right',padx=4)
            button(bar,'صرف كمية',self.out_stock).pack(side='right',padx=4)
        else:
            button(bar,'طلب إضافة كمية',lambda:self.request('in')).pack(side='right',padx=4)
            button(bar,'طلب صرف كمية',lambda:self.request('out')).pack(side='right',padx=4)
        button(bar,'تحديث',self.refresh).pack(side='left',padx=4)
        if self.manager: button(bar,'تصدير Excel',self.export_excel).pack(side='left',padx=4)
        self.refresh()
    def refresh(self):
        for frame in (self.items_list,self.moves_list,self.requests_list):
            if frame is None: continue
            for w in frame.winfo_children(): w.destroy()
        self.item_rows={}
        for x in list_items():
            kind='منتج جاهز للبيع' if x['item_type']=='ready' else 'خامة / استخدام داخلي'
            txt=f"{x['id']} | {x['name']} | {kind} | المتاح: {x['quantity']:g} {x['unit']} | تكلفة الوحدة: {float(x.get('avg_cost') or 0):.2f} جنيه | قيمة الرصيد: {float(x['quantity'] or 0)*float(x.get('avg_cost') or 0):.2f} جنيه | حد التنبيه: {x['min_quantity']:g}"
            b=ctk.CTkButton(self.items_list,text=txt,anchor='e',fg_color='#403327' if x['id']==self.selected else '#302923',command=lambda iid=x['id']:self.select(iid))
            b.pack(fill='x',padx=6,pady=3); self.item_rows[x['id']]=x
        for m in (list_movements() if self.manager else []):
            typ={'opening':'رصيد افتتاحي','in':'إضافة','out':'صرف','adjustment':'تسوية'} .get(m['movement_type'],m['movement_type'])
            label(self.moves_list,f"{m['created_at']} | {m['item_name']} | {typ} {m['quantity']:g} {m['unit']} | الرصيد {m['balance_after']:g} | {m.get('actor') or ''} | {m.get('notes') or ''}",13,TEXT).pack(anchor='e',fill='x',padx=8,pady=3)
        for r in list_requests() if self.manager else list_requests(user_id=self.user['id']):
            status={'pending':'معلق','approved':'مقبول','rejected':'مرفوض'}.get(r['status'],r['status'])
            row=ctk.CTkFrame(self.requests_list,fg_color='#302923'); row.pack(fill='x',padx=6,pady=4)
            label(row,f"#{r['id']} | {r['item_name']} | {'إضافة' if r['request_type']=='in' else 'صرف'} {r['quantity']:g} {r['unit']} | {r['requester']} | {r['reason']} | {status}",13,TEXT).pack(side='right',padx=8,pady=8)
            if self.manager and r['status']=='pending':
                button(row,'موافقة',lambda rid=r['id']:self.decide(rid,True),True).pack(side='left',padx=4)
                button(row,'رفض',lambda rid=r['id']:self.decide(rid,False)).pack(side='left',padx=4)
    def select(self,iid): self.selected=iid; self.refresh()
    def export_excel(self):
        try:
            from datetime import datetime
            filename=f"ليالي_وسط_البلد_تقرير_المخزون_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
            selected=filedialog.asksaveasfilename(
                parent=self, title='اختار مكان حفظ تقرير المخزون',
                defaultextension='.xlsx', initialfile=filename,
                filetypes=[('Excel Workbook','*.xlsx')]
            )
            if not selected:
                return
            path=export_inventory_excel(selected)
            messagebox.showinfo('تم التصدير',f'تم حفظ تقرير المخزون بنجاح:\n{path}',parent=self)
        except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)
    def add_item(self):
        # Scrollable, explicitly labelled form so all fields remain visible on
        # different Windows scaling / screen sizes.
        w=ctk.CTkToplevel(self)
        w.title('إضافة صنف للمخزن')
        w.geometry('500x700')
        w.minsize(460,620)
        w.configure(fg_color=BG)
        w.transient(self)
        w.grab_set()

        form=ctk.CTkScrollableFrame(w, fg_color=BG, corner_radius=0)
        form.pack(fill='both', expand=True, padx=12, pady=10)
        label(form,'بيانات الصنف',21,GOLD,True).pack(pady=(8,16))

        def field_title(text):
            label(form,text,14,TEXT,True).pack(anchor='e',padx=20,pady=(8,3))

        field_title('اسم الصنف')
        name=enable_rtl_entry(ctk.CTkEntry(form,placeholder_text='مثال: بن تركي',width=390,justify='right'))
        name.pack(pady=3)

        type_labels={'خامات (استخدام داخلي)':'raw','منتجات جاهزة للبيع':'ready'}
        field_title('نوع الصنف')
        typ=ctk.StringVar(value='خامات (استخدام داخلي)')
        ctk.CTkOptionMenu(form,values=list(type_labels.keys()),variable=typ,width=390).pack(pady=3)

        unit_values=['قطعة','كيلو','جرام','لتر','ملليلتر','عبوة','كرتونة','كيس','زجاجة']
        field_title('وحدة القياس')
        unit=ctk.StringVar(value='قطعة')
        ctk.CTkOptionMenu(form,values=unit_values,variable=unit,width=390).pack(pady=3)

        field_title('الكمية الحالية / الرصيد الافتتاحي')
        opening=ctk.CTkEntry(form,placeholder_text='اكتب الكمية الموجودة حاليًا',width=390,justify='right')
        opening.pack(pady=3)

        field_title('تكلفة الوحدة بالجنيه (اختياري)')
        cost=ctk.CTkEntry(form,placeholder_text='مثال: 350',width=390,justify='right')
        cost.pack(pady=3)

        def save():
            try:
                opening_qty=opening.get().strip() or '0'
                cost_value=cost.get().strip() or '0'
                if float(opening_qty)<0: raise ValueError('الكمية الحالية لا يمكن أن تكون سالبة.')
                if float(cost_value)<0: raise ValueError('تكلفة الوحدة لا يمكن أن تكون سالبة.')
                add_item(clean_entry(name),type_labels[typ.get()],unit.get(),opening_qty,0,cost_value,self.user['id'])
                w.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror('خطأ',str(e),parent=w)

        button(form,'حفظ الصنف',save,True,width=390).pack(pady=(18,16))
    def _quantity_form(self,title,callback,with_cost=False,with_unit=False):
        if not self.selected: messagebox.showwarning('تنبيه','اختر صنفًا أولًا.',parent=self); return
        item=self.item_rows[self.selected]
        w=ctk.CTkToplevel(self); w.title(title); w.geometry('420x390' if with_unit else '400x330'); w.configure(fg_color=BG); w.grab_set()
        label(w,f"{title}: {item['name']}",19,GOLD,True).pack(pady=15)
        q=ctk.CTkEntry(w,placeholder_text='أدخل الكمية',width=300); q.pack(pady=8)
        selected_unit=None
        if with_unit:
            base=(item.get('unit') or '').strip()
            unit_options=[base]
            if base in ('كيلو','جرام'): unit_options=['كيلو','جرام']
            elif base in ('لتر','ملليلتر'): unit_options=['لتر','ملليلتر']
            selected_unit=ctk.StringVar(value=base)
            label(w,'وحدة الكمية',13,TEXT).pack(pady=(5,2))
            ctk.CTkOptionMenu(w,values=unit_options,variable=selected_unit,width=300).pack(pady=5)
        cost=None
        if with_cost:
            cost=ctk.CTkEntry(w,placeholder_text='تكلفة الوحدة',width=300); cost.pack(pady=8); cost.insert(0,str(item['avg_cost']))
        note=enable_rtl_entry(ctk.CTkEntry(w,placeholder_text='ملاحظات / سبب الحركة',width=300,justify='right')); note.pack(pady=8)
        def go():
            try:
                amount=float(q.get())
                if amount<=0: raise ValueError('أدخل كمية أكبر من صفر.')
                if with_unit and selected_unit:
                    chosen=selected_unit.get(); base=(item.get('unit') or '').strip()
                    # Convert the entered amount into the item's stored base unit.
                    if chosen=='جرام' and base=='كيلو': amount/=1000
                    elif chosen=='كيلو' and base=='جرام': amount*=1000
                    elif chosen=='ملليلتر' and base=='لتر': amount/=1000
                    elif chosen=='لتر' and base=='ملليلتر': amount*=1000
                callback(item,str(amount),cost.get() if cost else None,clean_entry(note))
                w.destroy(); self.refresh()
            except Exception as e: messagebox.showerror('خطأ',str(e),parent=w)
        button(w,'تأكيد',go,True,width=300).pack(pady=12)
    def in_stock(self): self._quantity_form('إضافة كمية',lambda i,q,c,n:stock_in(i['id'],q,c,self.user['id'],n),True)
    def out_stock(self): self._quantity_form('صرف كمية',lambda i,q,c,n:stock_out(i['id'],q,self.user['id'],n),with_unit=True)
    def request(self,kind):
        if not self.selected: messagebox.showwarning('تنبيه','اختر صنفًا أولًا.',parent=self); return
        item=self.item_rows[self.selected]; w=ctk.CTkToplevel(self); w.geometry('400x280'); w.configure(fg_color=BG); w.grab_set()
        label(w,'طلب '+('إضافة' if kind=='in' else 'صرف')+' مخزون',20,GOLD,True).pack(pady=15)
        q=ctk.CTkEntry(w,placeholder_text='الكمية',width=300); q.pack(pady=8)
        reason=enable_rtl_entry(ctk.CTkEntry(w,placeholder_text='سبب الطلب',width=300,justify='right')); reason.pack(pady=8)
        def send():
            try: create_request(item['id'],kind,q.get(),clean_entry(reason),self.user['id']); w.destroy(); self.refresh(); messagebox.showinfo('تم','تم إرسال الطلب للمدير.',parent=self)
            except Exception as e: messagebox.showerror('خطأ',str(e),parent=w)
        button(w,'إرسال الطلب',send,True,width=300).pack(pady=12)
    def decide(self,rid,approve):
        try: decide_request(rid,approve,self.user['id']); self.refresh(); messagebox.showinfo('تم','تم تنفيذ القرار.',parent=self)
        except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)
