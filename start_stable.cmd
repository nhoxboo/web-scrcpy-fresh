@echo off
REM Web-Scrcpy-Fresh Stable Startup Script
setlocal enabledelayedexpansion

cd /d "%~dp0"
echo [%date% %time%] Starting web-scrcpy-fresh...
set DISABLE_DEV_BANNER=1
set DISABLE_ADB_KEEPALIVE=1

:restart
python.exe app.py --port 8000
echo [%date% %time%] Process exited with code !errorlevel!
timeout /t 5 /nobreak
goto restart
