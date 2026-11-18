import customtkinter as ctk
from tkinter import messagebox
from services.settings import get_settings, save_settings
from ui.common import BG, PANEL, GOLD, TEXT, MUTED, button, label,show_child_window

class Settings(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        show_child_window(self, parent)
        self.title("إعدادات الطباعة")
        self.geometry("650x620")
        self.configure(fg_color=BG)
        settings = get_settings()
        current = settings["receipt_width_mm"]
        outer = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=16)
        outer.pack(fill="both", expand=True, padx=28, pady=28)
        label(outer, "إعدادات الطباعة", 26, GOLD, True).pack(anchor="e", padx=24, pady=(25, 8))
        label(outer, "حدد عرض رول الورق الحراري المستخدم في الطابعة.", 15, MUTED).pack(anchor="e", padx=24, pady=(0, 22))
        self.mode = ctk.StringVar(value=str(current) if current in (58, 80) else "custom")
        choices = ctk.CTkFrame(outer, fg_color="transparent")
        choices.pack(fill="x", padx=24)
        for value, caption in [("80", "80 مم - رول عريض"), ("58", "58 مم - رول صغير"), ("custom", "مقاس مخصص")]:
            ctk.CTkRadioButton(choices, text=caption, variable=self.mode, value=value,
                               text_color=TEXT, fg_color=GOLD, command=self._toggle_custom).pack(anchor="e", pady=9)
        self.custom = ctk.CTkEntry(outer, placeholder_text="اكتب العرض بالمليمتر، مثال: 72", justify="right", width=260)
        self.custom.pack(anchor="e", padx=24, pady=(14, 5))
        if self.mode.get() == "custom": self.custom.insert(0, str(current))
        self._toggle_custom()
        label(outer, "يمكنك تغيير المقاس لاحقًا من نفس الشاشة. ستُستخدم الإعدادات في الإيصالات الجديدة.", 12, MUTED, wraplength=540).pack(anchor="e", padx=24, pady=15)
        label(outer, "طابعة المطبخ عبر الشبكة", 18, GOLD, True).pack(anchor="e", padx=24, pady=(12, 5))
        self.kitchen_ip = ctk.CTkEntry(outer, width=260, justify="right", placeholder_text="IP طابعة المطبخ")
        self.kitchen_ip.insert(0, settings.get("kitchen_printer_ip", "192.168.8.12"))
        self.kitchen_ip.pack(anchor="e", padx=24, pady=4)
        self.kitchen_port = ctk.CTkEntry(outer, width=260, justify="right", placeholder_text="Port")
        self.kitchen_port.insert(0, str(settings.get("kitchen_printer_port", 9100)))
        self.kitchen_port.pack(anchor="e", padx=24, pady=4)
        button(outer, "حفظ إعدادات الطابعات", self.save, True, height=42, width=220).pack(anchor="e", padx=24, pady=(10, 22))

    def _toggle_custom(self):
        self.custom.configure(state="normal" if self.mode.get() == "custom" else "disabled")

    def save(self):
        try:
            width = int(self.custom.get()) if self.mode.get() == "custom" else int(self.mode.get())
            save_settings({"receipt_width_mm": width, "kitchen_printer_ip": self.kitchen_ip.get(), "kitchen_printer_port": int(self.kitchen_port.get())})
            messagebox.showinfo("تم الحفظ", f"تم حفظ عرض الورق: {width} مم", parent=self)
            self.destroy()
        except (ValueError, TypeError) as exc:
            messagebox.showerror("مقاس غير صحيح", str(exc) or "اكتب رقمًا صحيحًا بين 40 و120 مم.", parent=self)
