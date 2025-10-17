@echo off
setlocal
cd /d "%~dp0"
set APP_NAME=TeamsIconMaker
py -3 -m pip install --upgrade pip >nul
py -3 -m pip install --upgrade pyinstaller Pillow >nul
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "%APP_NAME%" ^
  teams_icon_app.py
echo.
echo EXE at .\dist\%APP_NAME%.exe
pause
