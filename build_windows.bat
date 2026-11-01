@echo off
REM Build HushKey on Windows.   Double-click this file, or run: build_windows.bat
REM Result: dist\HushKey\HushKey.exe  (keep the whole HushKey folder together)
REM The installer (HushKey-Windows.exe) is built by GitHub; see the README.
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt pyinstaller
python -m unittest || goto :error
python app.py --selftest || goto :error
python packaging\make_version_info.py || goto :error
pyinstaller --noconfirm --clean --windowed --noupx --name HushKey --icon assets\HushKey.ico --add-data "assets;assets" --collect-data customtkinter --version-file packaging\version_info.txt app.py || goto :error
echo.
echo Done! Your app is at: dist\HushKey\HushKey.exe
pause
exit /b 0
:error
echo Build failed.
pause
exit /b 1
