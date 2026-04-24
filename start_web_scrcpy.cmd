@echo off
setlocal
cd /d C:\Users\Administrator\.openclaw\workspace\web-scrcpy-fresh

REM Stop old python app.py instances on port 8000 (best effort)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
  taskkill /PID %%p /F >nul 2>&1
)

REM Start web-scrcpy in background
start "web-scrcpy" /min cmd /c "cd /d C:\Users\Administrator\.openclaw\workspace\web-scrcpy-fresh && python app.py --port 8000 --video_bit_rate 2000000"

endlocal
