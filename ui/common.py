import customtkinter as ctk

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # The app remains launchable; install requirements for correct Arabic shaping.
    arabic_reshaper = None
    get_display = None


def rtl_text(value):
    """Shape Arabic for display in Tk/CustomTkinter without changing stored text."""
    if not isinstance(value, str) or not any("\u0600" <= ch <= "\u06ff" for ch in value):
        return value
    if arabic_reshaper is None or get_display is None:
        return value
    try:
        return get_display(arabic_reshaper.reshape(value), base_dir="R")
    except Exception:
        return value


_RLM = "\u200f"
_LRM = "\u200e"

def enable_rtl_entry(entry):
    """Configure an input for right alignment without injecting bidi marks.

    Tk/CustomTkinter Entry widgets must keep the user's logical Unicode text
    untouched. Prefixing RLM changes the bidi run and was causing Arabic word
    order to appear reversed in some Windows/Tk builds.
    """
    try:
        entry.configure(justify="right")
    except Exception:
        pass
    return entry

def clean_entry(entry):
    """Return logical text, removing legacy direction marks from old entries."""
    value = entry.get()
    return value.replace(_RLM, "").replace(_LRM, "").strip()

BG="#171513"; PANEL="#24201C"; GOLD="#D6A354"; TEXT="#F5F0E8"; MUTED="#B8AA98"

def label(parent,text,size=15,color=TEXT,bold=False,**kwargs):
    return ctk.CTkLabel(parent,text=rtl_text(text),text_color=color,font=ctk.CTkFont(size=size,weight="bold" if bold else "normal"),**kwargs)

def button(parent,text,command,primary=False,**kwargs):
    return ctk.CTkButton(parent,text=rtl_text(text),command=command,
        fg_color=GOLD if primary else "#51483D",
        hover_color="#B98538" if primary else "#655848",
        text_color="#1B1712" if primary else TEXT,**kwargs)


def show_child_window(window, parent):
    """Configure workspace windows as normal top-level windows on Windows.

    Do not mark these pages transient: on Windows/Tk this can give a child
    window tool-window decorations and hide the maximize button. Keep the
    parent relationship for application ownership, but allow normal resizing.
    """
    try:
        window.resizable(True, True)
        window.minsize(700, 500)
    except Exception:
        pass
    def raise_window():
        try:
            if window.winfo_exists():
                window.lift()
                window.focus_force()
        except Exception:
            pass
    window.after(80, raise_window)
