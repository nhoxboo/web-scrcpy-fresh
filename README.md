# Remote Android nhoxboo

Điều khiển thiết bị Android từ trình duyệt — stream video độ trễ thấp + chuột, bàn phím, clipboard sync 2 chiều, chụp ảnh / quay video, quick controls, **Virtual Desktop** (DeX-style cho mọi Android 11+). Stack: Python (Flask + Socket.IO + eventlet) + scrcpy + adb. Bản private dùng nội bộ.

Live demo (Nam): http://nhoxboo.changeip.co:8000/

---

## Mục lục
1. [Tính năng chính](#tính-năng-chính)
2. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
3. [Quick start](#quick-start)
4. [Cài ADB](#cài-adb-android-debug-bridge)
5. [Triển khai production](#triển-khai-production)
   - [Docker (DỄ NHẤT)](#a-docker-dễ-nhất)
   - [Gunicorn + eventlet](#b-gunicorn--eventlet-tự-cấu-hình)
   - [Dev server (KHÔNG cho production)](#c-dev-server--werkzeug-không-dùng-cho-production)
6. [HTTPS + reverse proxy](#https--reverse-proxy)
7. [Tinh chỉnh chất lượng video](#tinh-chỉnh-chất-lượng-video)
8. [Hướng dẫn sử dụng UI](#hướng-dẫn-sử-dụng-ui)
9. [Kết nối thiết bị: USB và Wi-Fi](#kết-nối-thiết-bị-usb-và-wi-fi)
10. [Quên mật khẩu / reset](#quên-mật-khẩu--reset)
11. [Audit log + health check](#audit-log--health-check)
12. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
13. [Bảo mật](#bảo-mật)
14. [Khắc phục sự cố](#khắc-phục-sự-cố)
15. [Phát triển](#phát-triển)
16. [License](#license)

---

## Tính năng chính

| Nhóm | Chi tiết |
|---|---|
| **Stream** | H.264 qua MSE + JMuxer; mặc định 60fps / 10 Mbps / max 1920px (chỉnh được qua env) |
| **Input** | UHID mouse + keyboard (cursor thật, click phải, scroll wheel, modifier) **HOẶC** touch + inject_keycode (toggle); slider tốc độ chuột 0.25× – 4×, tuỳ chọn acceleration |
| **Clipboard** | Sync 2 chiều browser ↔ device (auto khi connect) |
| **Multi-touch** | Pointer Events: pinch-to-zoom, 2-3 ngón |
| **Capture** | 📷 Screenshot (Ctrl+Shift+S) + ⏺ Quay video (Ctrl+Shift+R, MediaRecorder webm/mp4) |
| **Virtual Desktop** | `--new-display=WxH/dpi` — desktop-style cho **mọi** Android 11+ (Samsung / Pixel / Xiaomi / OnePlus...). Shift-click để chỉnh kích thước. |
| **Desktop chrome** | Top bar Back/Home/Recent + bottom taskbar (clock, battery) + app drawer khi Virtual Desktop bật |
| **Quick Controls** | Wifi / BT / Mobile data / Vol / Lock / Power / Camera / Settings / Reboot — qua adb shell whitelist |
| **APK install** | Cài APK từ file upload hoặc URL |
| **File push** | Upload file vào `/sdcard/Download/` |
| **Macro** | Record / Replay chuỗi tap, swipe, type |
| **Hotkey** | Map phím tắt browser → key Android (custom) |
| **Game mode** | Chế độ pointer lock cho game FPS |
| **Wireless ADB Pair** | Pair + connect qua Wi-Fi (Android 11+, không cần USB sau lần pair đầu) |
| **Multi-device** | Trang `/devices` chọn thiết bị, mỗi session có serial riêng |
| **Auth** | Login + đổi mật khẩu, password hash bcrypt, session timeout, rate-limit, force-kick |
| **Telemetry** | FPS / Mbps HUD overlay (Ctrl+Shift+H), audit log JSONL |

## Yêu cầu hệ thống

- **OS**: Windows 10+, macOS 11+, Linux x64
- **Python**: 3.10 / 3.11 / 3.12 (matrix CI)
- **adb**: Android Platform Tools — xem [Cài ADB](#cài-adb-android-debug-bridge) bên dưới
- **Thiết bị Android**: Android 7+ (Virtual Desktop cần Android 11+, UHID cần scrcpy server 2.4+ — đã có sẵn 3.1 trong repo)
- **Browser**: Chrome / Edge / Firefox 110+ (Safari hỗ trợ một phần — UHID + clipboard cần HTTPS)

---

## Quick start

```bash
git clone https://github.com/nhoxboo/web-scrcpy-fresh-private.git
cd web-scrcpy-fresh-private

# 1. Cài Python deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Cài adb (xem section dưới nếu chưa có)
adb version    # phải in ra "Android Debug Bridge version ..."

# 3. Cấu hình env
cp .env.example .env
echo "FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env

# 4. Chạy thử (dev mode — sẽ in cảnh báo Werkzeug, OK để test local)
python app.py
# → http://localhost:8000  (login: admin / admin123 — đổi ngay!)
```

Cắm thiết bị Android, bật **Developer options → USB debugging**, chấp nhận dialog "Allow USB debugging" lần đầu. `adb devices` phải hiện serial của máy. Mở `http://localhost:8000`, đăng nhập, video phải hiện sau ~2-3 giây.

> **Production**: KHÔNG dùng `python app.py` — xem [Triển khai production](#triển-khai-production).

---

## Cài ADB (Android Debug Bridge)

ADB là binary từ Google, không phải Python package — phải cài riêng.

### Linux
```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y android-tools-adb

# Arch / Manjaro
sudo pacman -S android-tools

# Fedora
sudo dnf install -y android-tools
```

### macOS
```bash
brew install --cask android-platform-tools
```

### Windows
1. Tải `platform-tools-latest-windows.zip` từ https://developer.android.com/tools/releases/platform-tools
2. Giải nén ra ví dụ `C:\platform-tools\`
3. Set environment variable: `ADB_PATH=C:\platform-tools\adb.exe` (hoặc thêm thư mục vào `PATH`)
4. Mở PowerShell mới → `adb version` phải chạy được

### Verify

```bash
adb version          # in version
adb devices          # list thiết bị (cắm phone + bật USB Debugging trước)
```

Nếu `adb devices` trả `unauthorized` → trên phone hãy chấp nhận dialog "Allow USB debugging" + tick "Always allow".

---

## Triển khai production

### a) Docker (DỄ NHẤT)

Image self-contained: Python 3.12 + gunicorn + eventlet + adb + healthcheck. State persist qua named volume.

```bash
cp .env.example .env
echo "FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
docker compose up -d
docker compose logs -f
```

- App: http://localhost:8000 (login lần đầu `admin` / `admin123` — đổi ngay)
- `auth.json` / `secret.key` / `audit.log` lưu trong volume `webscrcpy-data` (persist qua `docker compose down`, mất khi `down -v`)
- USB Linux: mặc định bind `/dev/bus/usb` + `privileged: true`. Trên Windows/macOS: gỡ 2 dòng đó trong `docker-compose.yml` rồi dùng [Wireless ADB Pair](#kết-nối-thiết-bị-usb-và-wi-fi).

```bash
docker compose build --no-cache              # rebuild khi đổi code
docker compose exec web python reset_password.py --username admin   # reset password
docker compose down                            # stop, giữ data
docker compose down -v                         # stop + xoá data (mất auth!)
```

### b) Gunicorn + eventlet (tự cấu hình)

Khi không dùng Docker (host trực tiếp / systemd):

```bash
pip install -r requirements-prod.txt
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export SESSION_COOKIE_SECURE=1   # CHỈ bật khi đứng sau HTTPS
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 wsgi:app
```

Hoặc qua [`honcho`](https://honcho.readthedocs.io/) (đọc `Procfile` có sẵn):
```bash
pip install honcho
honcho start
```

systemd unit mẫu:
```ini
# /etc/systemd/system/web-scrcpy.service
[Unit]
Description=Remote Android nhoxboo
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/srv/web-scrcpy-fresh-private
EnvironmentFile=/srv/web-scrcpy-fresh-private/.env
ExecStart=/srv/web-scrcpy-fresh-private/.venv/bin/gunicorn \
  --worker-class eventlet -w 1 \
  --bind 127.0.0.1:8000 \
  --access-logfile - --error-logfile - \
  wsgi:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now web-scrcpy
sudo journalctl -fu web-scrcpy
```

> **Bắt buộc 1 worker.** State scrcpy session là process-local; nhiều worker sẽ tranh nhau device. Để scale, đặt mỗi container/máy 1 device và load-balance bằng reverse proxy.

### c) Dev server / Werkzeug (KHÔNG dùng cho production)

`python app.py` chạy Werkzeug **single-threaded** — stutter ngay khi có 1 user thật connect. Dev mode in cảnh báo lớn ở console; tắt bằng `DISABLE_DEV_BANNER=1`.

Cách tự kiểm tra mình đang chạy production hay dev:
```bash
curl -I http://your-host:8000/
# Server: gunicorn  → đúng (production)
# Server: Werkzeug/X → SAI (đang dùng dev server, sẽ lag)
```

---

## HTTPS + reverse proxy

Một số API browser **bắt buộc HTTPS**: clipboard read/write, MediaRecorder trên một số browser, screen capture. Trên HTTP các tính năng này silent fail.

### Caddy (1 file, auto Let's Encrypt)

```caddyfile
# /etc/caddy/Caddyfile
your-domain.com {
    reverse_proxy 127.0.0.1:8000 {
        header_up X-Forwarded-Proto {scheme}
    }
}
```
```bash
sudo systemctl restart caddy
# Caddy tự lấy cert Let's Encrypt — domain phải trỏ về IP máy trước
```
Trong app: set `TRUST_PROXY=1` + `SESSION_COOKIE_SECURE=1` để Flask trust X-Forwarded-* và đóng cookie chỉ qua HTTPS.

### Nginx
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # Socket.IO / WebSocket
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 600s;
    }
}
```

---

## Tinh chỉnh chất lượng video

Defaults: **10 Mbps / 60 fps / max edge 1920px** — phù hợp LAN gigabit hoặc Wi-Fi 5+ trên flagship 4K (Galaxy Fold/Ultra, iPhone 14+, Pixel 7+).

| Mạng | `SCRCPY_VIDEO_BIT_RATE` | `SCRCPY_MAX_SIZE` | `SCRCPY_MAX_FPS` |
|---|---|---|---|
| LAN gigabit / cùng router | 15000000 (15M) | 1920 | 60 |
| Wi-Fi 5+ trong nhà | **10000000** (default) | **1920** (default) | **60** (default) |
| Wi-Fi yếu / Wi-Fi public | 4000000 (4M) | 1280 | 30 |
| LTE / 4G / VPN | 2000000 (2M) | 960 | 30 |
| Phone <1080p (Galaxy A series) | 6000000 (6M) | 0 (native) | 60 |

Set qua `.env` rồi restart:
```bash
SCRCPY_VIDEO_BIT_RATE=4000000
SCRCPY_MAX_SIZE=1280
SCRCPY_MAX_FPS=30
```

> **Tại sao max_size=1920 lại sắc nét hơn 0 (native)?** Bitrate 10M cho 4K phải chia đều cho ~8 triệu pixel → bit/pixel thấp → blocky. Cùng bitrate cap về 2 triệu pixel (1920×1080) → 4× bit/pixel → sắc hơn rõ. Chỉ tắt cap (set 0) khi phone có native res nhỏ (<1080p).

### HUD bandwidth/FPS để debug

```js
localStorage.setItem('streamHud', '1'); location.reload();
```
Hoặc Ctrl+Shift+H (chuyển trạng thái nhanh). Overlay góc dưới hiện FPS thực + Mbps (~1s averaging). Nếu FPS ≪ MAX_FPS → bottleneck là decoder browser; nếu Mbps ≈ BIT_RATE setting → đang giới hạn bởi mạng.

---

## Hướng dẫn sử dụng UI

### Toolbar (theo thứ tự trái → phải)

| Icon | Nút | Chức năng |
|---|---|---|
| ⏻ | Power | nhấn nút nguồn |
| 🔉🔊 | Vol −/+ | volume |
| ← | Back | back key |
| 🏠 | Home | home key |
| ▭ | Recent | recents |
| ⟳ | Rotate | quay màn (auto-refit MSE) |
| ⛶ | Fullscreen | F11 mode |
| 📷 | Screenshot | Ctrl+Shift+S — chụp ảnh PNG ở native res |
| ⏺ | Recording | Ctrl+Shift+R — quay webm/mp4 → tải về |
| 🖥 | Virtual Desktop | `--new-display=1920x1080/160` — Shift-click để chỉnh resolution/dpi |
| 🎚 | Quick Controls | panel mở ra với các nút nhanh |
| 🖱 | UHID toggle | bật/tắt chuột+phím thật (default ON) |
| | UHID speed | slider tốc độ + checkbox accel |
| 🔌 | Reconnect | reconnect socket (xoá MSE rồi nối lại) |
| 📦 | Cài APK | upload file .apk hoặc dán URL |
| ⤴ | Push file | upload file vào `/sdcard/Download/` |
| ⌨ | Keyboard typing | textarea → inject_text vào device |
| ⏺ Macro | record / stop / play / clear | record chuỗi thao tác để chạy lại |
| ⌨ Hotkey | gán phím tắt | map phím browser → keycode Android |
| 🎮 Game mode | pointer lock | dành cho game FPS |
| 🔍 | Zoom −/+/reset | scale video trong shell |

### Phím tắt

| Phím | Hành động |
|---|---|
| Ctrl+Shift+S | Screenshot |
| Ctrl+Shift+R | Toggle recording |
| Ctrl+Shift+H | Toggle stream HUD |
| ESC | Thoát pointer lock (khi UHID mouse đang lock) |

### Clipboard sync

Sau khi connect, browser sẽ xin permission "Read/write clipboard" → accept để sync 2 chiều. Nếu deny:
- Browser → device: vẫn được (không cần permission, chỉ đọc selection)
- Device → browser: fallback hiện preview text trong status bar

### Tiếng Việt

UHID bypass IME, nên gõ tiếng Việt với UHID ON sẽ không có dấu. 2 cách giải quyết:
1. Tắt UHID toggle khi cần gõ → input đi qua touch + inject_keycode (qua IME)
2. Bấm nút Keyboard typing (⌨) → mở textarea → gõ tiếng Việt với IME của browser → server inject_text vào device (giữ dấu)

---

## Kết nối thiết bị: USB và Wi-Fi

### USB
1. Cắm cáp data (không phải cáp sạc-only)
2. Bật **Settings → About → tap Build number 7 lần** để mở Developer options
3. **Developer options → USB debugging: ON**
4. Lần cắm đầu phone hỏi "Allow USB debugging?" → tick "Always allow", chấp nhận
5. `adb devices` trên host phải hiện serial → mở web → Devices page → device hiện trong list

### Wi-Fi (ADB pair, Android 11+)

Trên trang `/devices`, scroll xuống "Pair via Wi-Fi" có 2 form:

**Form 1 — Pair lần đầu** (mỗi máy chỉ cần 1 lần):
1. Trên phone: Developer options → **Wireless debugging** → ON
2. Vào "Wireless debugging" → "Pair device with pairing code"
3. Hộp thoại hiện `IP:PORT` + 6-digit code (ví dụ `192.168.1.42:38543` + `123456`)
4. Trên web: nhập `host:port` + code → **Pair**
5. Backend chạy `adb pair host:port code` — phone báo "Successfully paired"

**Form 2 — Connect** (sau khi đã pair):
- Phone hiển thị 1 IP:port khác cho **connect** (thường `:5555` hoặc port động)
- Nhập `host:port` → **Connect**
- Backend chạy `adb connect host:port` → device hiện trong list

> Sau khi pair lần đầu, lần sau chỉ cần Connect (cùng Wi-Fi). Phone có thể đổi IP/port khi reboot Wi-Fi → vẫn dùng được pair cũ, chỉ Connect lại.

---

## Quên mật khẩu / reset

```bash
# Local
python reset_password.py --username admin
# nhập password mới (ẩn) — phải >= 8 ký tự

# Docker
docker compose exec web python reset_password.py --username admin
```

Nếu muốn về default `admin/admin123`: xoá `auth.json` (hoặc `docker compose down -v` xoá volume) → app tự tạo lại.

---

## Audit log + health check

### `/healthz`
JSON `{"status":"ok","has_client":bool}`. Healthcheck Docker dùng endpoint này.

### Audit log
Default `audit.log` (override `AUDIT_LOG_FILE`). Mỗi dòng JSONL ghi: timestamp, user, IP, action, detail.

```bash
tail -f audit.log | python -m json.tool   # xem realtime, format đẹp
```

Sự kiện được log: login (success/fail), logout, password change, /api/install, /api/push, /api/quick/*, session kick, scrcpy start/stop, wireless pair/connect.

---

## Cấu trúc thư mục

```
.
├── app.py                  # Flask app, routes, Socket.IO server
├── scrcpy.py               # Scrcpy lifecycle (spawn, NALU parser, control msg)
├── wsgi.py                 # gunicorn entry point
├── reset_password.py       # CLI reset
├── requirements.txt        # core deps (Flask, eventlet, ...)
├── requirements-prod.txt   # gunicorn
├── requirements-dev.txt    # pytest, ruff
├── Procfile                # honcho / Heroku-style
├── Dockerfile              # production image (Python 3.12 + adb + gunicorn)
├── docker-compose.yml      # 1-command deploy
├── .env.example            # template env vars
├── scrcpy-server           # Java server JAR (push to device on connect)
├── static/                 # CSS, vendored JS (jmuxer, fontawesome, socket.io)
│   ├── css/glass.css       # liquid glass design tokens
│   └── js/input.js         # touch + UHID encoders
├── templates/              # Jinja2 templates
│   ├── index.html          # main control UI (stream + toolbar)
│   ├── login.html
│   ├── change_password.html
│   └── devices.html
├── tests/                  # pytest, 67 tests
│   ├── test_auth.py
│   ├── test_devices.py
│   ├── test_install.py
│   ├── test_launcher.py
│   ├── test_quick_wireless.py
│   ├── test_reset_password.py
│   ├── test_scrcpy_parser.py
│   ├── test_session.py
│   └── test_template_bindings.py
├── .github/workflows/ci.yml   # ruff + pytest matrix 3.10/3.11/3.12
└── .pre-commit-config.yaml    # ruff format + check
```

---

## Bảo mật

- **Password hash**: bcrypt (`werkzeug.security.generate_password_hash`)
- **Session**: cookie-signed, lifetime 24h (`SESSION_LIFETIME_SECONDS`), SameSite=Lax
- **Login rate-limit**: 8 attempts / 5 phút / IP
- **Password change rate-limit**: 10 attempts / 5 phút / user
- **CSRF**: token trên mọi form POST (`csrf_token()`)
- **Single-client lock**: chỉ 1 socket Active được điều khiển; client khác bị reject → có thể "force kick" để giành lại
- **Whitelist `adb shell`**: Quick Controls chỉ cho phép subset commands cố định, không có shell injection surface
- **APK install size cap**: 500 MB default (`MAX_INSTALL_SIZE_MB`)
- **TRUST_PROXY**: chỉ bật khi đứng sau reverse proxy (Caddy/nginx) → tránh IP spoofing trong audit log

> **Không expose ra Internet công khai** mà không có HTTPS + auth mạnh + rate-limit. Đây là bản private dùng nội bộ.

### Đổi mật khẩu mặc định ngay sau lần login đầu tiên

App sẽ chuyển bạn đến `/change-password` nếu phát hiện đang dùng default `admin/admin123`. Chọn password ≥ 8 ký tự.

---

## Khắc phục sự cố

### "WS lỗi: Đã có client khác đang điều khiển thiết bị"
Có 1 tab/browser khác đang dùng. Mở `/devices` → "Force kick" để đá session cũ ra (yêu cầu owner cùng IP hoặc admin role).

### Stream lag / stutter
1. Kiểm tra header `Server:` (xem section [Dev server](#c-dev-server--werkzeug-không-dùng-cho-production)) — phải là `gunicorn`
2. Bật HUD (Ctrl+Shift+H) → check FPS, Mbps thực tế
3. Nếu Mbps gần đụng `SCRCPY_VIDEO_BIT_RATE` → mạng giới hạn → giảm bitrate hoặc max_size theo bảng [Tinh chỉnh](#tinh-chỉnh-chất-lượng-video)
4. Nếu FPS thấp nhưng Mbps thấp → decoder browser yếu → giảm `SCRCPY_MAX_SIZE` xuống 1280 / 960

### `adb devices` hiện `unauthorized`
Phone chưa nhận USB debugging → unplug → plug lại → trên phone tick "Always allow" rồi accept.

### `adb devices` không hiện gì
- Cáp data (không phải sạc-only) — đa số cáp Type-C đi kèm sạc nhanh đều OK
- USB debugging chưa bật trong Developer options
- Trên Linux: cần `udev rules` cho ADB; cài `android-tools-adb` đã set sẵn, nếu chưa thì thêm rule:
  ```
  # /etc/udev/rules.d/51-android.rules
  SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666"   # Samsung
  SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666"   # Google / Pixel
  ```
  rồi `sudo udevadm control --reload`

### Virtual Desktop không kích hoạt
Cần Android 11+. Trên Android 10 hoặc cũ hơn, server scrcpy reject `--new-display`. Kiểm tra version: `adb shell getprop ro.build.version.release`.

### Clipboard không sync
Browser cần permission. Trên HTTP (không HTTPS) browser sẽ silent fail. Triển khai HTTPS như section [HTTPS](#https--reverse-proxy) để fix.

### Quick Controls "Wifi ON" không bật
Một số OEM (MIUI, ColorOS, OneUI mới) chặn `svc wifi enable` từ adb. UI sẽ hiện stderr cụ thể. Workaround: bật tay trong Settings.

### "Werkzeug single-threaded" cảnh báo trên console
Bạn đang chạy `python app.py` (dev mode) — chuyển sang gunicorn để tránh stutter. Xem [Triển khai production](#triển-khai-production). Nếu cố tình chạy dev (debug local), set `DISABLE_DEV_BANNER=1` để tắt banner.

### Reset hoàn toàn
```bash
# Xoá auth, secret, audit log
rm -f auth.json secret.key audit.log

# Hoặc với Docker
docker compose down -v
```

---

## Phát triển

### Setup dev environment
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

### Chạy tests
```bash
pytest -q                    # 67 tests, ~10s
pytest tests/test_auth.py    # 1 file
pytest -k login              # filter theo pattern
ruff check .                 # lint
ruff format .                # format
```

### Branch + commit convention
```
git checkout -b devin/$(date +%s)-tên-tính-năng
# commit: type(scope): mô tả
# vd: feat(uhid): thêm slider tốc độ chuột
```

CI: `.github/workflows/ci.yml` chạy ruff + pytest cho Python 3.10 / 3.11 / 3.12 trên mọi push + PR.

### Cấu hình env (xem `.env.example` đầy đủ)
| Var | Default | Mô tả |
|---|---|---|
| `FLASK_SECRET_KEY` | random nếu không set | Cookie-signing key — set 1 lần cố định cho production |
| `SCRCPY_VIDEO_BIT_RATE` | `10000000` | bps |
| `SCRCPY_MAX_FPS` | `60` | fps |
| `SCRCPY_MAX_SIZE` | `1920` | longest edge px, 0 = native |
| `SCRCPY_DISPLAY_ID` | `0` | Android display id (advanced — external HDMI dock) |
| `SCRCPY_LOCAL_PORT` | `5555` | adb forward local port |
| `MAX_INSTALL_SIZE_MB` | `500` | APK upload cap |
| `MAX_PUSH_SIZE_MB` | `500` | push upload cap |
| `SESSION_LIFETIME_SECONDS` | `86400` | 24h |
| `TRUST_PROXY` | `0` | bật khi đứng sau reverse proxy |
| `SESSION_COOKIE_SECURE` | `0` | bật khi đứng sau HTTPS |
| `DISABLE_DEV_BANNER` | `0` | ẩn cảnh báo Werkzeug |
| `AUTH_FILE` | `./auth.json` | path file auth (Docker: `/data/auth.json`) |
| `SECRET_FILE` | `./secret.key` | path file secret key |
| `AUDIT_LOG_FILE` | `./audit.log` | path audit log |

### Mở rộng

Hệ thống module:
- `app.py` — routes, auth, Socket.IO. Helpers `_save_auth`, `_audit`, decorator `@login_required`.
- `scrcpy.py` — class `Scrcpy` quản lý subprocess + `_parse_nalus` chuyển H.264 stream từ scrcpy sang dạng JMuxer ăn được.
- `static/js/input.js` — encoder cho touch (legacy) + UHID (mouse + keyboard).
- `templates/index.html` — UI tất-cả-trong-một (1300+ dòng JS inline; có kế hoạch tách `static/js/app.js`).

PR mới nên:
1. Thêm test trong `tests/` (mẫu: `tests/test_quick_wireless.py`)
2. Cập nhật `tests/test_template_bindings.py` nếu thêm button mới
3. Update `.env.example` nếu thêm env var
4. Update README section liên quan
5. CI matrix phải xanh trên 3.10 / 3.11 / 3.12

---

## License

MIT. Xem `LICENSE.txt`. Project sử dụng [scrcpy](https://github.com/Genymobile/scrcpy) (Apache 2.0) — file `scrcpy-server` JAR là binary từ release scrcpy chính thức.
