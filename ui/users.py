import customtkinter as ctk
from tkinter import messagebox
from services.users import all_users,add_user,edit_user,toggle_user,change_password
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,rtl_text,show_child_window

class Users(ctk.CTkToplevel):
    def __init__(self,parent,user):
        super().__init__(parent); self.user=user; self.selected=None
        show_child_window(self, parent)
        self.title("إدارة المستخدمين"); self.geometry("950x620"); self.configure(fg_color=BG)
        label(self,"إدارة المستخدمين",26,TEXT,True).pack(anchor="e",padx=22,pady=18)
        button(self,"+ إضافة مستخدم",self.form,True).pack(anchor="w",padx=22)
        self.listbox=ctk.CTkScrollableFrame(self,fg_color=PANEL); self.listbox.pack(fill="both",expand=True,padx=22,pady=15)
        bar=ctk.CTkFrame(self,fg_color="transparent"); bar.pack(fill="x",padx=22,pady=12)
        button(bar,"تعديل",self.edit).pack(side="right",padx=4)
        button(bar,"تغيير كلمة المرور",self.password).pack(side="right",padx=4)
        button(bar,"تفعيل / تعطيل",self.toggle).pack(side="right",padx=4)
        self.refresh()
    def refresh(self):
        for w in self.listbox.winfo_children(): w.destroy()
        self.rows={}
        for u in all_users():
            text=f"{u['id']}  |  {u['username']}  |  {u['full_name']}  |  {'مدير' if u['role']=='manager' else 'كاشير'}  |  {'نشط' if u['is_active'] else 'موقوف'}"
            b=ctk.CTkButton(self.listbox,text=rtl_text(text),anchor="e",fg_color="#403327" if u["id"]==self.selected else "#302923",
                            command=lambda uid=u["id"]:self.select(uid))
            b.pack(fill="x",pady=3); self.rows[u["id"]]=u
    def select(self,uid): self.selected=uid; self.refresh()
    def form(self,u=None):
        w=ctk.CTkToplevel(self); w.geometry("420x460"); w.configure(fg_color=BG); w.grab_set()
        label(w,"إضافة مستخدم" if not u else "تعديل مستخدم",22,GOLD,True).pack(pady=20)
        en=ctk.CTkEntry(w,width=320,placeholder_text="اسم المستخدم",justify="right"); en.pack(pady=8)
        fn=ctk.CTkEntry(w,width=320,placeholder_text="الاسم الكامل",justify="right"); fn.pack(pady=8)
        pw=ctk.CTkEntry(w,width=320,placeholder_text="كلمة المرور (8 أحرف على الأقل)",show="●",justify="right")
        if not u: pw.pack(pady=8)
        role=ctk.StringVar(value=u["role"] if u else "cashier")
        ctk.CTkOptionMenu(w,values=["cashier","manager"],variable=role,width=320).pack(pady=10)
        if u: en.insert(0,u["username"]); fn.insert(0,u["full_name"])
        def save():
            try:
                if u: edit_user(u["id"],en.get(),fn.get(),role.get(),self.user["id"])
                else: add_user(en.get(),fn.get(),pw.get(),role.get(),self.user["id"])
                w.destroy(); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e),parent=w)
        button(w,"حفظ",save,True,width=320).pack(pady=20)
    def edit(self):
        if self.selected: self.form(self.rows[self.selected])
        else: messagebox.showwarning("تنبيه","اختر مستخدماً أولاً.")
    def password(self):
        if not self.selected: messagebox.showwarning("تنبيه","اختر مستخدماً أولاً."); return
        w=ctk.CTkToplevel(self); w.geometry("380x220"); w.configure(fg_color=BG); w.grab_set()
        e=ctk.CTkEntry(w,width=300,placeholder_text="كلمة المرور الجديدة",show="●"); e.pack(pady=25)
        def save():
            try: change_password(self.selected,e.get(),self.user["id"]); w.destroy(); messagebox.showinfo("تم","تم تغيير كلمة المرور.")
            except Exception as x: messagebox.showerror("خطأ",str(x),parent=w)
        button(w,"حفظ",save,True).pack()
    def toggle(self):
        if not self.selected: messagebox.showwarning("تنبيه","اختر مستخدماً أولاً."); return
        u=self.rows[self.selected]
        try: toggle_user(u["id"],not bool(u["is_active"]),self.user["id"]); self.refresh()
        except Exception as e: messagebox.showerror("خطأ",str(e))
