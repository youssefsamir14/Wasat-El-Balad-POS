import os, sys, tempfile, subprocess
from pathlib import Path
from html import escape
from services.settings import get_settings

def make_receipt_html(invoice, items, cafe_name="ليالي وسط البلد", width_mm=None):
    width_mm = int(width_mm or get_settings()["receipt_width_mm"])
    if not 40 <= width_mm <= 120:
        width_mm = 80
    printable = max(34, width_mm - 6)
    rows = "".join(
        f"<tr><td>{escape(str(x['product_name']))}</td><td>{x['quantity']}</td><td>{x['line_total']:.2f}</td></tr>"
        for x in items
    )
    return f"""<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>إيصال {escape(str(invoice['number']))}</title>
    <style>
    @page {{ size: {width_mm}mm auto; margin: 2mm; }}
    * {{ box-sizing: border-box; }}
    html,body {{ margin:0; padding:0; }}
    body {{ font-family: Tahoma,Arial,sans-serif; width:{printable}mm; margin:0 auto; color:#111; font-size:11px; }}
    h2,p {{ text-align:center; margin:4px 0; }} h2 {{font-size:18px}}
    .meta {{font-size:10px; overflow-wrap:anywhere}}
    table {{ width:100%; border-collapse:collapse; margin-top:9px; table-layout:fixed; }}
    th,td {{ border-bottom:1px dashed #777; padding:5px 1px; text-align:right; font-size:10px; overflow-wrap:anywhere; }}
    th:first-child,td:first-child {{width:48%}} th:nth-child(2),td:nth-child(2) {{width:18%;text-align:center}}
    th:last-child,td:last-child {{width:34%;text-align:left;direction:ltr}}
    .total {{font-size:15px;font-weight:bold;text-align:center;margin:12px 0}}
    .thanks {{margin-top:10px}}
    @media screen {{ body {{ margin:18px auto; padding:8px; box-shadow:0 0 5px #aaa; }} }}
    @media print {{ body {{ margin:0 auto; }} }}
    </style></head><body>
    <h2>{escape(cafe_name)}</h2><p>فاتورة بيع</p>
    <p class='meta'>{escape(str(invoice['number']))}</p><p class='meta'>{escape(str(invoice['created_at']))}</p>
    {f"<p class='meta'>الصالة: {escape(str(invoice.get('salon_name')))}</p>" if invoice.get('salon_name') else ''}
    {f"<p class='meta'>رقم الترابيزة: {escape(str(invoice.get('table_number')))}</p>" if invoice.get('table_number') else ''}
    <table><thead><tr><th>الصنف</th><th>كمية</th><th>جنيه</th></tr></thead><tbody>{rows}</tbody></table>
    <p>الإجمالي قبل الخصم: {float(invoice.get('subtotal', invoice['total'])):.2f} جنيه</p><p>الخصم: {float(invoice.get('discount', 0)):.2f} جنيه</p><p class='total'>الإجمالي: {invoice['total']:.2f} جنيه</p><p class='thanks'>شكراً لزيارتكم</p>
    <script>window.addEventListener('load',()=>{{setTimeout(()=>window.print(),350);}});</script>
    </body></html>"""

def print_receipt(invoice, items):
    html = make_receipt_html(invoice, items)
    fd, path = tempfile.mkstemp(suffix=".html", prefix="wasat_receipt_")
    os.close(fd)
    Path(path).write_text(html, encoding="utf-8")
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
    return path


def print_temporary_receipt(cart, subtotal, discount, total, table_number=None, salon_name=None):
    """Print a pro-forma bill without creating a saved invoice."""
    from datetime import datetime
    items=[{"product_name":x["name"],"quantity":int(x["quantity"]),"line_total":float(x["price"])*int(x["quantity"])} for x in cart]
    inv={"number":"مؤقتة - غير مدفوعة","created_at":datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),"subtotal":subtotal,"discount":discount,"total":total,"table_number":table_number,"salon_name":salon_name}
    html=make_receipt_html(inv,items)
    html=html.replace('<p>فاتورة بيع</p>', '<p>فاتورة مؤقتة - غير نهائية</p>')
    
    fd,path=tempfile.mkstemp(suffix='.html',prefix='wasat_prebill_'); os.close(fd); Path(path).write_text(html,encoding='utf-8')
    if sys.platform=='win32': os.startfile(path)
    elif sys.platform=='darwin': subprocess.Popen(['open',path])
    else: subprocess.Popen(['xdg-open',path])
    return path


def print_kitchen_ticket(cart, table_number=None, printer_ip=None, printer_port=None, salon_name=None):
    """Print a full-width 80mm kitchen ticket matching the customer receipt layout,
    but omit every monetary value. Sends ESC/POS raster data over TCP/IP.
    """
    import socket
    from datetime import datetime
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display

    if not cart:
        raise ValueError("السلة فارغة")
    settings = get_settings()
    printer_ip = str(printer_ip or settings.get("kitchen_printer_ip", "192.168.8.12"))
    printer_port = int(printer_port or settings.get("kitchen_printer_port", 9100))
    width = 576  # full printable width for an 80mm / 203dpi thermal printer
    margin = 28
    font_candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "tahoma.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    font_path = next((x for x in font_candidates if x.exists()), None)
    if font_path is None:
        raise RuntimeError("لم يتم العثور على خط عربي للطباعة")

    # Font sizes mirror the normal 80mm receipt, with no price column.
    title_font = ImageFont.truetype(str(font_path),  42)
    subtitle_font = ImageFont.truetype(str(font_path), 36)
    meta_font = ImageFont.truetype(str(font_path), 28)
    header_font = ImageFont.truetype(str(font_path), 30)
    item_font = ImageFont.truetype(str(font_path), 34)
    footer_font = ImageFont.truetype(str(font_path), 30)

    def rtl(value):
        return get_display(arabic_reshaper.reshape(str(value)))

    def text_width(draw, value, font):
        b = draw.textbbox((0, 0), value, font=font)
        return b[2] - b[0]

    # Build a spacious receipt-style layout, using the whole paper width.
    rows = []
    rows.append((rtl("ليالي وسط البلد"), title_font, 62, "center"))
    rows.append((rtl("طلب تحضير مشروبات"), subtitle_font, 54, "center"))
    now = datetime.now().astimezone().strftime("%Y-%m-%d   %H:%M")
    rows.append((rtl(now), meta_font, 46, "center"))
    if salon_name not in (None, ""):
        rows.append((rtl(f"الصالة: {salon_name}"), meta_font, 50, "center"))
    if table_number not in (None, ""):
        rows.append((rtl(f"رقم الترابيزة: {table_number}"), meta_font, 50, "center"))
    rows.append(("line", None, 24, "center"))
    rows.append((rtl("الصنف"), header_font, 48, "right"))
    for item in cart:
        name = str(item.get("name", item.get("product_name", "")))
        qty = int(item.get("quantity", 1))
        rows.append((rtl(name), item_font, 54, "right"))
        rows.append((rtl(f"الكمية: {qty}"), meta_font, 44, "left"))
        rows.append(("line", None, 22, "center"))
    rows.append((rtl("يرجى تجهيز الطلب"), footer_font, 58, "center"))

    height = sum(row[2] for row in rows) + 28
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    y = 12
    for value, font, line_h, align in rows:
        if value == "line":
            yy = y + line_h // 2
            draw.line((margin, yy, width - margin, yy), fill=0, width=2)
        else:
            tw = text_width(draw, value, font)
            if align == "center":
                x = (width - tw) // 2
            elif align == "right":
                x = width - margin - tw
            else:
                x = margin
            draw.text((x, y + 2), value, font=font, fill=0)
        y += line_h

    image = image.convert("1")
    pixels = image.load()
    width_bytes = (width + 7) // 8
    height_px = image.height
    raster = bytearray()
    for yy in range(height_px):
        for xb in range(width_bytes):
            byte = 0
            for bit in range(8):
                xx = xb * 8 + bit
                if xx < width and pixels[xx, yy] == 0:
                    byte |= 0x80 >> bit
            raster.append(byte)
    xL, xH = width_bytes & 0xFF, (width_bytes >> 8) & 0xFF
    yL, yH = height_px & 0xFF, (height_px >> 8) & 0xFF
    payload = b"\x1b@" + b"\x1dv0\x00" + bytes([xL, xH, yL, yH]) + bytes(raster) + b"\n\n\n" + b"\x1dV\x00"
    with socket.create_connection((printer_ip, printer_port), timeout=5) as sock:
        sock.sendall(payload)
    return True
