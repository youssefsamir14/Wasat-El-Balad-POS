import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import date
from tkinter import messagebox, simpledialog
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,rtl_text,show_child_window,enable_rtl_entry,clean_entry
from services.operations import add_expense,add_income,finance_summary,product_analysis,create_rental,rentals,return_rental,add_employee_wage,employee_wage_payments,finance_transactions,employee_monthly_wage_summary

class Finance(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); self.user=user; self.title('المصروفات والإيرادات'); self.geometry('850x650'); self.configure(fg_color=BG)
        show_child_window(self, parent)
        label(self,'إدارة المصروفات والإيرادات',25,GOLD,True).pack(pady=15)
        tabs=ctk.CTkTabview(self); tabs.pack(fill='both',expand=True,padx=20,pady=10)
        ex=tabs.add('تسجيل مصروف'); inc=tabs.add('تسجيل إيراد'); wages=tabs.add('أجور الموظفين'); summary=tabs.add('الملخص المالي')
        self._form(ex,'نوع المصروف','مثال: كهرباء / مياه / إيجار',lambda a,d,v,dt:add_expense(a,d,v,self.user['id'],dt),'expenses')
        self._form(inc,'مصدر الإيراد','مثال: إيراد آخر',lambda a,d,v,dt:add_income(a,d,v,self.user['id'],dt),'income')
        self._wage_form(wages)
        self.sum_label=label(summary,'',20,TEXT); self.sum_label.pack(pady=30); button(summary,'تحديث الملخص',self.refresh,True).pack(); self.refresh()
    def _form(self,parent,title,placeholder,fn,kind):
        body=ctk.CTkScrollableFrame(parent,fg_color=BG)
        body.pack(fill='both',expand=True,padx=8,pady=6)
        label(body,title,16,TEXT).pack(pady=(15,5)); a=enable_rtl_entry(ctk.CTkEntry(body,placeholder_text=placeholder,width=400,justify='right')); a.pack(pady=7)
        d=enable_rtl_entry(ctk.CTkEntry(body,placeholder_text='بيان / ملاحظات (اختياري)',width=400,justify='right')); d.pack(pady=7)
        label(body,'التاريخ',13,MUTED).pack(pady=(5,0))
        day=DateEntry(body,width=22,date_pattern='yyyy-mm-dd',locale='en_US'); day.pack(pady=7)
        v=ctk.CTkEntry(body,placeholder_text='المبلغ بالجنيه',width=400,justify='right'); v.pack(pady=7)
        history=ctk.CTkScrollableFrame(body,fg_color=PANEL,height=170); history.pack(fill='both',expand=True,padx=10,pady=8)
        def refresh_history():
            for w in history.winfo_children(): w.destroy()
            rows=finance_transactions(kind)
            if not rows:
                label(history,'لا توجد عمليات مسجلة حتى الآن.',13,MUTED).pack(pady=10)
                return
            for r in rows:
                desc=f"#{r['id']} | {r['title']} | {r['amount']:.2f} جنيه | {r['created_at']}"
                if r.get('description'): desc += f" | {r['description']}"
                label(history,desc,12,TEXT).pack(anchor='e',padx=8,pady=4)
        def save():
            try:
                fn(clean_entry(a),clean_entry(d),v.get(),day.get_date().strftime('%Y-%m-%d'))
                messagebox.showinfo('تم','تم التسجيل بنجاح.',parent=self)
                a.delete(0,'end'); d.delete(0,'end'); v.delete(0,'end')
                refresh_history(); self.refresh()
            except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)
        button(body,'حفظ',save,True,width=180).pack(pady=10)
        button(body,'تحديث السجل',refresh_history,width=150).pack(pady=(0,10))
        refresh_history()
    def _wage_form(self,parent):
        label(parent,'تسجيل دفعة أجر موظف',18,GOLD,True).pack(pady=(18,8))
        name=enable_rtl_entry(ctk.CTkEntry(parent,placeholder_text='اسم الموظف',width=380,justify='right')); name.pack(pady=6)
        period=enable_rtl_entry(ctk.CTkEntry(parent,placeholder_text='الفترة: يوم / أسبوع / شهر (اختياري)',width=380,justify='right')); period.pack(pady=6)
        amount=ctk.CTkEntry(parent,placeholder_text='المبلغ المدفوع بالجنيه',width=380,justify='right'); amount.pack(pady=6)
        label(parent,'تاريخ دفع الأجر',13,MUTED).pack(pady=(4,0))
        wage_date=DateEntry(parent,width=22,date_pattern='yyyy-mm-dd',locale='en_US'); wage_date.pack(pady=6)
        notes=enable_rtl_entry(ctk.CTkEntry(parent,placeholder_text='ملاحظات (اختياري)',width=380,justify='right')); notes.pack(pady=6)
        # Monthly employee payment total: sums recorded payments only (not attendance or accrued wages).
        monthly=ctk.CTkFrame(parent,fg_color=PANEL)
        monthly.pack(fill='x',padx=15,pady=(8,4))
        label(monthly,'إجمالي ما استلمه الموظف خلال الشهر',16,GOLD,True).pack(pady=(8,4))
        filter_row=ctk.CTkFrame(monthly,fg_color='transparent')
        filter_row.pack(pady=4)
        monthly_name=enable_rtl_entry(ctk.CTkEntry(filter_row,placeholder_text='اسم الموظف كما هو مسجل',width=210,justify='right'))
        monthly_name.pack(side='right',padx=5)
        monthly_date=DateEntry(filter_row,width=14,date_pattern='yyyy-mm-dd',locale='en_US')
        monthly_date.pack(side='right',padx=5)
        monthly_result=label(monthly,'اختار الموظف والشهر لعرض إجمالي الدفعات.',14,TEXT)
        monthly_result.pack(pady=(4,8))
        def calculate_monthly():
            try:
                chosen=monthly_date.get_date().strftime('%Y-%m')
                result=employee_monthly_wage_summary(clean_entry(monthly_name),chosen)
                monthly_result.configure(text=(
                    f"{result['employee_name']} | {chosen} | عدد الدفعات: {result['payment_count']} | "
                    f"إجمالي المستلم: {result['total_received']:.2f} جنيه"))
            except Exception as e:
                messagebox.showerror('خطأ',str(e),parent=self)
        button(filter_row,'حساب إجمالي الشهر',calculate_monthly,True,width=150).pack(side='right',padx=5)
        history=ctk.CTkScrollableFrame(parent,fg_color=PANEL,height=150); history.pack(fill='both',expand=True,padx=15,pady=8)
        def refresh_history():
            for w in history.winfo_children(): w.destroy()
            for r in employee_wage_payments():
                label(history,f"{r['employee_name']} | {r['period'] or 'بدون فترة'} | {r['amount']:.2f} جنيه | {r['created_at']}",13,TEXT).pack(anchor='e',padx=8,pady=3)
        def save():
            try:
                add_employee_wage(clean_entry(name),clean_entry(period),amount.get(),clean_entry(notes),self.user['id'],wage_date.get_date().strftime('%Y-%m-%d'))
                messagebox.showinfo('تم','تم تسجيل دفعة الأجر وإضافتها للمصروفات مرة واحدة.',parent=self)
                for e in (name,period,amount,notes): e.delete(0,'end')
                wage_date.set_date(date.today())
                refresh_history(); self.refresh()
            except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)
        button(parent,'تسجيل دفعة الأجر',save,True,width=200).pack(pady=8)
        refresh_history()
    def refresh(self):
        s=finance_summary(); self.sum_label.configure(text=f"مبيعات الفواتير: {s['sales']:.2f} جنيه\nإيرادات أخرى: {s['income']:.2f} جنيه\nالمصروفات: {s['expenses']:.2f} جنيه\n\nالصافي: {s['net']:.2f} جنيه")

class Rentals(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); show_child_window(self, parent); self.user=user; self.title('تأجير الطاولات والكراسي'); self.geometry('1050x720'); self.configure(fg_color=BG)
        label(self,'تسجيل تأجير جديد',24,GOLD,True).pack(pady=10)
        form=ctk.CTkFrame(self,fg_color=PANEL); form.pack(fill='x',padx=15,pady=8)
        self.fields={}
        specs=[('person_name','اسم الشخص'),('phone','رقم التليفون'),('table_count','عدد الطاولات'),('chair_count','عدد الكراسي'),('table_price','سعر الطاولة'),('chair_price','سعر الكرسي'),('discount','الخصم بالجنيه'),('paid','المبلغ المدفوع'),('notes','ملاحظات')]
        for i,(key,hint) in enumerate(specs):
            ent=ctk.CTkEntry(form,placeholder_text=hint,justify='right',width=190); ent.grid(row=i//3,column=2-(i%3),padx=8,pady=8); self.fields[key]=ent
        button(form,'حفظ عملية التأجير',self.save,True,width=220).grid(row=3,column=1,pady=10)
        label(self,'سجل التأجير وحالة المرتجعات',20,TEXT,True).pack(pady=8)
        self.list=ctk.CTkScrollableFrame(self,fg_color=PANEL); self.list.pack(fill='both',expand=True,padx=15,pady=8); self.refresh()
    def save(self):
        try:
            data={k:e.get() for k,e in self.fields.items()}; data['table_count']=data['table_count'] or 0; data['chair_count']=data['chair_count'] or 0
            for k in ('table_price','chair_price','discount','paid'): data[k]=data[k] or 0
            rid=create_rental(data,self.user['id']); messagebox.showinfo('تم',f'تم تسجيل التأجير رقم {rid}',parent=self)
            for e in self.fields.values(): e.delete(0,'end')
            self.refresh()
        except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)
    def refresh(self):
        for w in self.list.winfo_children(): w.destroy()
        for r in rentals():
            status={'out':'لم يرجع','partial':'رجع جزء','returned':'تم الإرجاع'}.get(r['status'],r['status'])
            row=ctk.CTkFrame(self.list,fg_color='#403327'); row.pack(fill='x',pady=4,padx=4)
            label(row,f"#{r['id']} | {r['person_name']} | الطاولات {r['returned_tables']}/{r['table_count']} رجعت | الكراسي {r['returned_chairs']}/{r['chair_count']} رجعت | الإجمالي {r['total']:.2f} | مدفوع {r['paid']:.2f} | متبقي {r['remaining']:.2f} | {status}",13,TEXT).pack(side='right',padx=8,pady=10)
            if r['status']!='returned': ctk.CTkButton(row,text=rtl_text('تسجيل إرجاع / دفعة'),width=150,command=lambda x=r:self.do_return(x)).pack(side='left',padx=5)
    def do_return(self,r):
        t=simpledialog.askinteger('المرتجعات','عدد الطاولات التي رجعت الآن؟',parent=self,minvalue=0); 
        if t is None:return
        c=simpledialog.askinteger('المرتجعات','عدد الكراسي التي رجعت الآن؟',parent=self,minvalue=0)
        if c is None:return
        p=simpledialog.askfloat('الدفع','مبلغ إضافي تم دفعه الآن؟',parent=self,minvalue=0,initialvalue=0)
        if p is None:return
        note=simpledialog.askstring('ملاحظات','ملاحظات (اختياري):',parent=self) or ''
        try: return_rental(r['id'],t,c,p,note,self.user['id']); self.refresh(); messagebox.showinfo('تم','تم تسجيل المرتجعات والدفع.',parent=self)
        except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)

class TablesAndAnalytics(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); show_child_window(self, parent); self.title('تحليل مبيعات المنتجات'); self.geometry('900x650'); self.configure(fg_color=BG)
        label(self,'تحليل مبيعات المنتجات',23,GOLD,True).pack(pady=18)
        label(self,'ترتيب المنتجات حسب الكمية المباعة والإيراد',14,MUTED).pack(pady=(0,10))
        self.products=ctk.CTkScrollableFrame(self,fg_color=PANEL)
        self.products.pack(fill='both',expand=True,padx=15,pady=10)
        self.refresh_products()
    def refresh_products(self):
        for w in self.products.winfo_children(): w.destroy()
        rows=product_analysis()
        if not rows:
            label(self.products,'لا توجد مبيعات مسجلة حتى الآن.',15,MUTED).pack(pady=20)
            return
        for p in rows:
            label(self.products,f"{p['product_name']}  |  الكمية المباعة: {p['quantity']}  |  صافي المبيعات: {p['revenue']:.2f} جنيه",15,TEXT).pack(anchor='e',padx=12,pady=7)
