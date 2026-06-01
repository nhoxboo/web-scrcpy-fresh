@echo off
setlocal
cd /d "%~dp0"

REM Stop old python app.py instances on port 8000 (best effort)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
  taskkill /PID %%p /F >nul 2>&1
)

REM Find python executable (local virtual env -> Espressif env -> System python)
set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%USERPROFILE%\.espressif\python_env\idf5.5_py3.11_env\Scripts\python.exe" (
  set "PYTHON_EXE=%USERPROFILE%\.espressif\python_env\idf5.5_py3.11_env\Scripts\python.exe"
)

echo Starting Web Scrcpy using: %PYTHON_EXE%
start "web-scrcpy" /min cmd /c "cd /d "%~dp0" && "%PYTHON_EXE%" app.py --port 8000 --video_bit_rate 2000000"

endlocal
