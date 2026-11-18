import customtkinter as ctk
from tkinter import messagebox
from services.auth import login
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,rtl_text
from ui.dashboard import Dashboard

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("ليالي وسط البلد POS")
        self.geometry("1366x768"); self.minsize(1100,650); self.configure(fg_color=BG)
        left=ctk.CTkFrame(self,fg_color=PANEL,corner_radius=18)
        left.pack(side="left",fill="both",expand=True,padx=(35,15),pady=35)
        label(left,"☕",72,GOLD).pack(pady=(145,5))
        label(left,"ليالي وسط البلد",42,GOLD,True).pack()
        label(left,"LAYALI WASAT EL BALAD",17,TEXT,True).pack(pady=8)
        label(left,"نظام الكاشير وإدارة المبيعات",18,MUTED).pack()
        right=ctk.CTkFrame(self,fg_color=PANEL,width=440,corner_radius=18)
        right.pack(side="right",fill="y",padx=(15,35),pady=35); right.pack_propagate(False)
        label(right,"تسجيل الدخول",30,TEXT,True).pack(pady=(150,30))
        self.username=ctk.CTkEntry(right,width=330,height=48,placeholder_text=rtl_text("اسم المستخدم"),justify="right")
        self.username.pack(pady=10)
        self.password=ctk.CTkEntry(right,width=330,height=48,placeholder_text=rtl_text("كلمة المرور"),show="●",justify="right")
        self.password.pack(pady=10); self.password.bind("<Return>",lambda e:self.submit())
        button(right,"دخول",self.submit,True,width=330,height=48).pack(pady=20)
        label(right,"الإصدار 1.2.0",12,MUTED).pack(side="bottom",pady=25)
        self.username.focus()
    def submit(self):
        user=login(self.username.get(),self.password.get())
        if not user:
            messagebox.showerror("فشل الدخول","بيانات الدخول غير صحيحة أو الحساب موقوف."); return
        self.withdraw(); Dashboard(self,user)
