@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Installa Python 3.12 o successivo da https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8000"
py -3 app.py
pause
