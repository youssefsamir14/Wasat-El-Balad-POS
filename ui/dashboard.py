import customtkinter as ctk
from tkinter import messagebox
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label
from services.sales import daily_summary
from services.approvals import pending_count

class Dashboard(ctk.CTkToplevel):
    def __init__(self,root,user):
        super().__init__(root); self.root=root; self.user=user
        self.title("ليالي وسط البلد POS"); self.geometry("1366x768"); self.minsize(1100,650); self.resizable(True, True)
        self.configure(fg_color=BG); self.protocol("WM_DELETE_WINDOW",self.logout)
        side=ctk.CTkFrame(self,width=230,fg_color=PANEL,corner_radius=0)
        side.pack(side="right",fill="y"); side.pack_propagate(False)
        label(side,"ليالي وسط البلد ☕",26,GOLD,True).pack(pady=(30,25))
        items=[("لوحة التحكم",self.home),("الكاشير",self.open_cashier),("الفواتير المؤقتة",self.open_drafts),("سجل المبيعات",self.open_sales),
               ("المنتجات",self.open_products),("المخازن",self.open_inventory),("المصروفات والإيرادات",self.open_finance),("تأجير الطاولات والكراسي",self.open_rentals),("تحليل مبيعات المنتجات",self.open_tables),("إعدادات الطباعة",self.open_settings)]
        if user["role"]=="manager":
            items += [("إدارة الصالات",self.open_salons)]
            items += [("المستخدمون",self.open_users),("طلبات الموافقة",self.open_approvals),("التقارير",self.open_reports)]
        for text,fn in items:
            if text == "طلبات الموافقة" and user["role"] == "manager":
                count = pending_count()
                text = f"طلبات الموافقة ({count})"
            button(side,text,fn,width=190,height=42).pack(pady=5,padx=15)
        # Keep the signed-in user's greeting in the empty lower area of the sidebar.
        label(side,self._welcome_text(),16,GOLD,True).pack(side="bottom",pady=(0,28))
        button(side,"تسجيل الخروج",self.logout,width=190,fg_color="#704333").pack(side="bottom",pady=16)
        self.body=ctk.CTkFrame(self,fg_color=BG); self.body.pack(side="left",fill="both",expand=True,padx=30,pady=25)
        self.home()
        if user["role"] == "manager":
            count = pending_count()
            if count:
                self.after(350, lambda n=count: messagebox.showinfo("طلبات موافقة جديدة", f"لديك {n} طلب/طلبات من الكاشير تحتاج مراجعتك.", parent=self))
    def _welcome_text(self):
        username = str(self.user.get("username", "")).strip().lower()
        if username == "admin" or self.user.get("role") == "admin":
            return "أهلاً Admin"
        if self.user.get("role") == "manager":
            return f"أهلاً مدير {self.user.get('full_name') or username}"
        return f"أهلاً {self.user.get('full_name') or username}"
    def clear(self):
        for x in self.body.winfo_children(): x.destroy()
    def home(self):
        self.clear(); s=daily_summary()
        label(self.body,"لوحة التحكم",30,TEXT,True).pack(anchor="e",pady=(10,25))
        cards=ctk.CTkFrame(self.body,fg_color="transparent"); cards.pack(fill="x",pady=30)
        for title,value in [("عدد فواتير اليوم",s["count"]),("مبيعات اليوم",f"{s['total']:.2f} جنيه")]:
            box=ctk.CTkFrame(cards,fg_color=PANEL,corner_radius=14); box.pack(side="right",fill="both",expand=True,padx=8)
            label(box,title,17,MUTED).pack(pady=(25,8)); label(box,str(value),28,GOLD,True).pack(pady=(0,25))
        label(self.body,"اختر القسم المطلوب من القائمة الجانبية.",16,MUTED).pack(anchor="e",pady=20)
    def open_cashier(self):
        from ui.cashier import Cashier
        Cashier(self,self.user)
    def open_drafts(self):
        from ui.drafts import InvoiceDrafts
        InvoiceDrafts(self,self.user)
    def open_sales(self):
        from ui.sales_history import SalesHistory
        SalesHistory(self,self.user)
    def open_inventory(self):
        from ui.inventory import Inventory
        Inventory(self,self.user)
    def open_products(self):
        from ui.products import Products
        Products(self,self.user)
    def open_users(self):
        if self.user["role"]!="manager": return
        from ui.users import Users
        Users(self,self.user)
    def open_finance(self):
        from ui.operations import Finance
        Finance(self,self.user)
    def open_rentals(self):
        from ui.operations import Rentals
        Rentals(self,self.user)
    def open_tables(self):
        from ui.operations import TablesAndAnalytics
        TablesAndAnalytics(self,self.user)
    def open_salons(self):
        if self.user["role"]!="manager": return
        from ui.salons import Salons
        Salons(self,self.user)
    def open_settings(self):
        from ui.settings import Settings
        Settings(self)
    def open_approvals(self):
        if self.user['role']!='manager': return
        from ui.approvals import Approvals
        Approvals(self,self.user)
    def open_reports(self):
        if self.user["role"]!="manager": return
        from ui.reports import Reports
        Reports(self)
    def logout(self):
        self.destroy(); self.root.deiconify()
