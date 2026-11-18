# PyInstaller spec for Wasat El Balad POS (Arabic GUI)
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ["bidi.algorithm", "arabic_reshaper", "tkcalendar", "babel"]
for package in ("customtkinter", "arabic_reshaper", "bidi", "tkcalendar", "babel"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["main.py"], pathex=[], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="WasatElBaladPOS",
    debug=False, bootloader_ignore_signals=False, strip=False,
    upx=True, console=False, disable_windowed_traceback=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=True,
    upx_exclude=[], name="WasatElBaladPOS",
)
