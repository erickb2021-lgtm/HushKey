@echo off
REM Build HushKey.exe on Windows.   Double-click this file, or run: build_windows.bat
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt pyinstaller
python -m unittest || goto :error
pyinstaller --noconfirm --onefile --windowed --name HushKey app.py || goto :error
echo.
echo Done! Your app is at: dist\HushKey.exe
pause
exit /b 0
:error
echo Build failed.
pause
exit /b 1
