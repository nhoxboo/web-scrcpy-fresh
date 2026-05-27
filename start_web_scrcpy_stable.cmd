@echo off
setlocal enableextensions
cd /d "%~dp0"

set "ADB=C:\Users\Administrator\.openclaw\workspace\platform-tools\adb.exe"
set "SERIAL=RFCRA1630YJ"
set "LOG=%~dp0startup-web-scrcpy.log"

echo [%%date%% %%time%%] ==== START stable launcher ====>> "%LOG%"

if not exist "%ADB%" (
  echo [%%date%% %%time%%] ERROR: adb not found at %ADB%>> "%LOG%"
  exit /b 1
)

"%ADB%" kill-server >> "%LOG%" 2>&1
"%ADB%" start-server >> "%LOG%" 2>&1

set "READY=0"
for /L %%i in (1,1,20) do (
  "%ADB%" devices > "%temp%\adb_devices.txt" 2>&1
  findstr /R /C:"^%SERIAL%[ ]*device" "%temp%\adb_devices.txt" >nul
  if not errorlevel 1 (
    set "READY=1"
    goto :runapp
  )
  timeout /t 2 /nobreak >nul
)

:runapp
if "%READY%"=="1" (
  echo [%%date%% %%time%%] Device ready: %SERIAL%>> "%LOG%"
) else (
  echo [%%date%% %%time%%] WARN: device not ready after wait, still starting app>> "%LOG%"
)

python app.py --serial %SERIAL% >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%%date%% %%time%%] EXIT code=%RC%>> "%LOG%"
exit /b %RC%
