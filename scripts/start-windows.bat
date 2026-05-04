@echo off
REM Remote Android nhoxboo - Windows production launcher (cmd.exe wrapper)
REM
REM Goi PowerShell script chinh ban canh. Su dung neu khong muon mo
REM PowerShell tay. Cu double-click file .bat hoac chay tu cmd:
REM   scripts\start-windows.bat
REM
REM Tham so duoc forward sang script PowerShell, vd:
REM   scripts\start-windows.bat -Port 9000 -BindHost 127.0.0.1

setlocal
cd /d "%~dp0\.."

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1" %*
exit /b %ERRORLEVEL%
