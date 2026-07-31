@echo off
setlocal
cd /d "%~dp0"

REM Stop old python instances
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000\|:443" ^| findstr LISTENING') do (
  taskkill /PID %%p /F >nul 2>&1
)

REM Find python executable
set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%USERPROFILE%\.espressif\python_env\idf5.5_py3.11_env\Scripts\python.exe" (
  set "PYTHON_EXE=%USERPROFILE%\.espressif\python_env\idf5.5_py3.11_env\Scripts\python.exe"
)

echo Starting Web Scrcpy HTTPS using: %PYTHON_EXE%
start "web-scrcpy-https" /min cmd /c "cd /d "%~dp0" && "%PYTHON_EXE%" run_https.py --host 0.0.0.0 --port 8000 --https-port 443 --ssl-cert certs\cert.pem --ssl-key certs\key.pem --video-bit-rate 2000000"

endlocal
