import customtkinter as ctk
from tkinter import messagebox
from services.operations import list_salons, add_salon, set_salon_active, delete_salon
from ui.common import BG, PANEL, GOLD, TEXT, MUTED, button, label, enable_rtl_entry

class Salons(ctk.CTkToplevel):
    def __init__(self, parent, user):
        super().__init__(parent)
        self.user=user
        self.title('إدارة الصالات')
        self.geometry('720x620')
        self.minsize(620,480)
        self.configure(fg_color=BG)
        outer=ctk.CTkFrame(self,fg_color=PANEL,corner_radius=14)
        outer.pack(fill='both',expand=True,padx=20,pady=20)
        label(outer,'إدارة الصالات',26,GOLD,True).pack(anchor='e',padx=20,pady=(20,8))
        label(outer,'أضف أسماء الصالات التي سيختار منها الكاشير عند تسجيل الطلب.',14,MUTED).pack(anchor='e',padx=20,pady=(0,14))
        form=ctk.CTkFrame(outer,fg_color='transparent'); form.pack(fill='x',padx=20)
        self.name=enable_rtl_entry(ctk.CTkEntry(form,placeholder_text='اسم الصالة، مثال: الصالة الداخلية',justify='right',height=40))
        self.name.pack(side='right',fill='x',expand=True,padx=(0,8))
        button(form,'إضافة صالة',self.add,True,width=130,height=40).pack(side='left')
        self.list=ctk.CTkScrollableFrame(outer,fg_color='#302923')
        self.list.pack(fill='both',expand=True,padx=20,pady=18)
        self.refresh()
    def refresh(self):
        for w in self.list.winfo_children(): w.destroy()
        rows=list_salons(active_only=False)
        if not rows:
            label(self.list,'لم تتم إضافة صالات بعد.',15,MUTED).pack(pady=25)
            return
        for salon in rows:
            row=ctk.CTkFrame(self.list,fg_color='#403327'); row.pack(fill='x',pady=4,padx=4)
            state='مفعّلة' if salon['is_active'] else 'متوقفة'
            label(row,f"{salon['name']} — {state}",16,TEXT,True).pack(side='right',padx=12,pady=12)
            if salon['is_active']:
                button(row,'إيقاف',lambda sid=salon['id']:self.toggle(sid,False),width=90).pack(side='left',padx=8,pady=6)
            else:
                button(row,'تفعيل',lambda sid=salon['id']:self.toggle(sid,True),width=90).pack(side='left',padx=8,pady=6)
            button(row,'حذف',lambda sid=salon['id'], name=salon['name']:self.remove(sid,name),width=80).pack(side='left',padx=8,pady=6)
    def add(self):
        try:
            add_salon(self.name.get())
            self.name.delete(0,'end'); self.refresh()
        except Exception as e: messagebox.showerror('تعذر إضافة الصالة',str(e),parent=self)
    def toggle(self,salon_id,active):
        try: set_salon_active(salon_id,active); self.refresh()
        except Exception as e: messagebox.showerror('خطأ',str(e),parent=self)

    def remove(self,salon_id,name):
        confirmed=messagebox.askyesno(
            'تأكيد حذف الصالة',
            f'هل تريد حذف صالة «{name}» من قائمة الصالات؟\n\nالفواتير القديمة ستحتفظ باسم الصالة المسجل بها، لكن الصالة لن تظهر بعد ذلك في قائمة الكاشير.',
            parent=self
        )
        if not confirmed:
            return
        try:
            delete_salon(salon_id)
            self.refresh()
        except Exception as e:
            messagebox.showerror('تعذر حذف الصالة',str(e),parent=self)
