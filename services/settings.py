import json
import os
from pathlib import Path

def _settings_path():
    base = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "WasatElBaladPOS"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"

def get_settings():
    defaults = {"receipt_width_mm": 80, "kitchen_printer_ip": "192.168.8.12", "kitchen_printer_port": 9100}
    path = _settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        width = int(data.get("receipt_width_mm", 80))
        if 40 <= width <= 120:
            defaults["receipt_width_mm"] = width
        ip = str(data.get("kitchen_printer_ip", defaults["kitchen_printer_ip"])).strip()
        if ip:
            defaults["kitchen_printer_ip"] = ip
        port = int(data.get("kitchen_printer_port", defaults["kitchen_printer_port"]))
        if 1 <= port <= 65535:
            defaults["kitchen_printer_port"] = port
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return defaults

def save_settings(settings):
    width = int(settings.get("receipt_width_mm", 80))
    if not 40 <= width <= 120:
        raise ValueError("عرض الورق يجب أن يكون بين 40 و120 مم")
    path = _settings_path()
    current = get_settings()
    ip = str(settings.get("kitchen_printer_ip", current["kitchen_printer_ip"])).strip()
    port = int(settings.get("kitchen_printer_port", current["kitchen_printer_port"]))
    if not ip or not 1 <= port <= 65535:
        raise ValueError("بيانات طابعة المطبخ غير صحيحة")
    path.write_text(json.dumps({"receipt_width_mm": width, "kitchen_printer_ip": ip, "kitchen_printer_port": port}, ensure_ascii=False, indent=2), encoding="utf-8")
    return width
