# Remote Android nhoxboo — Windows production launcher
#
# Mục đích: trên Windows không có gunicorn, nên không thể dùng
# `gunicorn --worker-class eventlet`. Thay vào đó cài eventlet rồi
# `python app.py` — Flask-SocketIO sẽ tự dùng eventlet WSGI server,
# tốc độ ngang gunicorn và không có cảnh báo Werkzeug.
#
# Cách chạy:
#   PowerShell -ExecutionPolicy Bypass -File scripts\start-windows.ps1
#
# Hoặc trong PowerShell mở sẵn:
#   .\scripts\start-windows.ps1
#
# Tham số:
#   -Port 8000           — đổi cổng listen (default 8000)
#   -Host 0.0.0.0        — bind host (default 0.0.0.0, dùng 127.0.0.1 nếu chỉ chạy local)
#   -SkipInstall         — bỏ qua bước `pip install -r requirements-prod.txt`
#   -GenerateSecret      — tạo FLASK_SECRET_KEY mới và ghi vào .env (chỉ chạy khi
#                          .env chưa có hoặc key đang mặc định)

[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$BindHost = '0.0.0.0',
    [switch]$SkipInstall,
    [switch]$GenerateSecret
)

$ErrorActionPreference = 'Stop'

# Cd về repo root (script nằm trong scripts/ nên Split-Path 2 lần).
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot
Write-Host "[start-windows] Repo: $repoRoot" -ForegroundColor Cyan

# 1) Đảm bảo có Python 3.10+
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    $pythonExe = (Get-Command py -ErrorAction SilentlyContinue).Source
}
if (-not $pythonExe) {
    throw 'Không tìm thấy Python. Cài Python 3.10+ từ https://www.python.org/downloads/windows/ rồi tick "Add to PATH".'
}
$pyVer = & $pythonExe --version 2>&1
Write-Host "[start-windows] Python: $pyVer" -ForegroundColor Cyan

# 2) venv nếu chưa có
$venvDir = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host '[start-windows] Tạo virtualenv .venv ...' -ForegroundColor Cyan
    & $pythonExe -m venv .venv
}
$pythonExe = $venvPython
Write-Host "[start-windows] Dùng Python venv: $pythonExe" -ForegroundColor Cyan

# 3) Cài deps (skip nếu user pass -SkipInstall)
if (-not $SkipInstall) {
    Write-Host '[start-windows] Cài requirements-prod.txt (eventlet, ...)' -ForegroundColor Cyan
    & $pythonExe -m pip install --upgrade pip | Out-Null
    & $pythonExe -m pip install -r requirements-prod.txt
    if ($LASTEXITCODE -ne 0) {
        throw 'pip install lỗi — kiểm tra network / requirements-prod.txt'
    }
}

# 4) Verify eventlet import được. Đây là điều kiện tiên quyết.
$check = & $pythonExe -c "import eventlet; print('eventlet', eventlet.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw 'eventlet không import được. Bỏ -SkipInstall hoặc chạy `pip install eventlet` thủ công.'
}
Write-Host "[start-windows] $check OK" -ForegroundColor Green

# 5) Verify adb
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbCmd) {
    if ($env:ADB_PATH -and (Test-Path $env:ADB_PATH)) {
        Write-Host "[start-windows] adb từ ADB_PATH: $env:ADB_PATH" -ForegroundColor Cyan
    } else {
        Write-Warning 'Không tìm thấy adb trong PATH. Tải platform-tools từ https://developer.android.com/tools/releases/platform-tools rồi set ADB_PATH hoặc thêm vào PATH.'
    }
} else {
    $adbVer = & adb version 2>&1 | Select-Object -First 1
    Write-Host "[start-windows] adb: $adbVer" -ForegroundColor Cyan
}

# 6) .env: tạo nếu thiếu, generate FLASK_SECRET_KEY nếu user yêu cầu
$envFile = Join-Path $repoRoot '.env'
if (-not (Test-Path $envFile)) {
    Write-Host '[start-windows] Copy .env.example -> .env' -ForegroundColor Cyan
    Copy-Item -Path '.env.example' -Destination '.env'
    $GenerateSecret = $true
}
if ($GenerateSecret) {
    $secret = & $pythonExe -c 'import secrets; print(secrets.token_hex(32))'
    $envContent = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
    if (-not $envContent) { $envContent = '' }
    if ($envContent -match '(?m)^FLASK_SECRET_KEY=') {
        $envContent = $envContent -replace '(?m)^FLASK_SECRET_KEY=.*', "FLASK_SECRET_KEY=$secret"
    } else {
        if ($envContent -and -not $envContent.EndsWith("`n")) { $envContent += "`r`n" }
        $envContent += "FLASK_SECRET_KEY=$secret`r`n"
    }
    Set-Content -Path $envFile -Value $envContent -NoNewline
    Write-Host '[start-windows] FLASK_SECRET_KEY mới đã ghi vào .env' -ForegroundColor Green
}

# 7) Load .env vào process env (don't override pre-existing values).
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim().Trim('"', "'")
        if (-not (Get-Item -Path "env:$key" -ErrorAction SilentlyContinue)) {
            Set-Item -Path "env:$key" -Value $val
        }
    }
}

# 8) Tắt cảnh báo Werkzeug (chúng ta đang dùng eventlet, nên banner không
# nên fire — nhưng phòng trường hợp eventlet import lỗi mid-flight).
if (-not $env:DISABLE_DEV_BANNER) { $env:DISABLE_DEV_BANNER = '1' }

Write-Host ''
Write-Host '==============================================================' -ForegroundColor Green
Write-Host " Remote Android nhoxboo — eventlet WSGI mode" -ForegroundColor Green
Write-Host " Listening on http://${BindHost}:$Port" -ForegroundColor Green
Write-Host " Press Ctrl+C to stop" -ForegroundColor Green
Write-Host '==============================================================' -ForegroundColor Green
Write-Host ''

# 9) Start. Eventlet sẽ được Flask-SocketIO tự pickup vì
# `SocketIO(app, async_mode=None)` auto-detect.
& $pythonExe app.py --host $BindHost --port $Port
