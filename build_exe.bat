@echo off
setlocal
cd /d "%~dp0"
echo [1/4] Creating virtual environment if needed...
if not exist .venv\Scripts\python.exe py -m venv .venv
call .venv\Scripts\activate.bat
if errorlevel 1 goto fail

echo [2/4] Installing project dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto fail
python -m pip install -r requirements.txt
if errorlevel 1 goto fail
python -m pip install pyinstaller
if errorlevel 1 goto fail

echo [3/4] Building EXE with Arabic shaping libraries included...
python -m PyInstaller --noconfirm --clean --windowed --onedir --name "WasatElBaladPOS" --collect-all customtkinter --collect-all arabic_reshaper --collect-all bidi --hidden-import=bidi.algorithm --hidden-import=arabic_reshaper main.py
if errorlevel 1 goto fail

echo [4/4] Build completed.
echo EXE: dist\WasatElBaladPOS\WasatElBaladPOS.exe
echo IMPORTANT: Copy the ENTIRE dist\WasatElBaladPOS folder, not the EXE alone.
pause
exit /b 0
:fail
echo.
echo BUILD FAILED. Copy the error shown above and send it for troubleshooting.
pause
exit /b 1
