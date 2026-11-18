import customtkinter as ctk, os
from tkinter import messagebox, filedialog
from services.reports import export_monthly_workbook
from ui.common import BG,PANEL,GOLD,TEXT,MUTED,button,label,show_child_window

class Reports(ctk.CTkToplevel):
    def __init__(self,parent):
        super().__init__(parent); self.title("التقارير"); self.geometry("650x360"); self.configure(fg_color=BG)
        show_child_window(self, parent)
        label(self,"تقارير Excel",26,TEXT,True).pack(pady=(35,15))
        label(self,"كل تصدير ينشئ ملفًا جديدًا: ملخص شهري، أداء الكاشير، وتفاصيل كل فاتورة.",15,MUTED).pack(pady=8)
        button(self,"تصدير / تحديث ملف Excel",self.export,True,width=300,height=45).pack(pady=20)
        self.path_label=label(self,"",12,MUTED); self.path_label.pack(pady=8)
    def export(self):
        try:
            from datetime import datetime
            filename = f"ليالي_وسط_البلد_التقرير_الشامل_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
            selected = filedialog.asksaveasfilename(
                parent=self,
                title="اختار مكان حفظ تقرير Excel",
                defaultextension=".xlsx",
                initialfile=filename,
                filetypes=[("Excel Workbook", "*.xlsx")],
            )
            if not selected:
                return
            path = export_monthly_workbook(output_path=selected)
            self.path_label.configure(text=str(path))
            messagebox.showinfo("تم", f"تم حفظ التقرير بنجاح:\n{path}", parent=self)
            if os.name == "nt":
                os.startfile(os.path.dirname(str(path)))
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)
