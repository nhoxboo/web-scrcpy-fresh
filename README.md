# 🎮 Web Scrcpy Fresh - Remote Android Control via Web Browser

**Web Scrcpy Fresh** là nền tảng web toàn diện để điều khiển thiết bị Android từ trình duyệt, dựa trên công nghệ `scrcpy`. Đây là bản private build được tối ưu cho sử dụng nội bộ với bảo mật, hiệu suất cao và UI/UX tiện lợi.

![Tech Stack](https://img.shields.io/badge/Python-3.10+-blue) ![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow) ![License](https://img.shields.io/badge/License-Apache%202.0-green)

---

## 📚 Mục lục

- [Tính năng nổi bật](#-tính-năng-nổi-bật)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cài đặt ADB](#-cài-đặt-adb-bắt-buộc)
- [Cài đặt nhanh](#-cài-đặt-nhanh)
- [Hướng dẫn chạy](#-hướng-dẫn-chạy)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Hướng dẫn đóng góp](#-hướng-dẫn-đóng-góp)
- [Tinh chỉnh hiệu suất](#-tinh-chỉnh-hiệu-suất)
- [Bảo mật](#-bảo-mật)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Tính năng nổi bật

### Điều khiển từ xa
- ✅ **Stream video realtime** từ Android qua trình duyệt
- ✅ **Multi-touch gestures**: pinch-to-zoom, 2-3 ngón chạm (Pointer Events)
- ✅ **Mouse/Keyboard control**: điều khiển chuột và bàn phím mượt mà
- ✅ **Pointer Lock (UHID mouse)**: giảm độ trễ trong gaming

### Quản lý hệ thống
- ✅ **Screenshot**: Ctrl+Shift+S — chụp ảnh màn hình
- ✅ **Screen recording**: Ctrl+Shift+R — quay video màn hình
- ✅ **Resolution override**: thay đổi độ phân giải / DPI qua ADB
  - Preset cho Galaxy Z Fold 3, tỷ lệ 16:9, 21:9, v.v.
- ✅ **Fullscreen mode**: video tự scale 100vw × 100vh

### Bảo mật & Quản lý
- ✅ **Trang đăng nhập** với xác thực mật khẩu
- ✅ **Đổi mật khẩu** trong-app
- ✅ **Reset mật khẩu** qua CLI khi quên
- ✅ **Session management**: cookie-based authentication
- ✅ **Health check endpoint** `/healthz` cho monitoring

### Triển khai Production
- ✅ **gunicorn + eventlet**: stream video mượt trên many clients
- ✅ **Reverse proxy ready**: Caddy / nginx + HTTPS support
- ✅ **Environment-based config**: dễ customize bitrate, FPS, resolution
- ✅ **Heroku-compatible Procfile**

---

## 🛠️ Yêu cầu hệ thống

### Bắt buộc
- **OS**: Windows, macOS, hoặc Linux
- **Python**: 3.10, 3.11, hoặc 3.12 (theo CI matrix)
- **ADB**: Android Debug Bridge (xem hướng dẫn [tại đây](#-cài-đặt-adb-bắt-buộc))
- **Android device**: đã bật USB Debugging

### Tùy chọn
- **gunicorn** (cho production)
- **honcho** (for running Procfile locally)
- **pytest, ruff** (cho development/testing)

---

## 🔧 Cài đặt ADB (bắt buộc)

Server cần `adb` để giao tiếp với thiết bị Android. Nếu `adb version` trả về "command not found", server sẽ báo lỗi `Không thể khởi động scrcpy`.

### Linux

**Debian / Ubuntu / Linux Mint:**
```bash
sudo apt update && sudo apt install -y android-tools-adb
```

**Arch / Manjaro:**
```bash
sudo pacman -S android-tools
```

**Fedora / RHEL:**
```bash
sudo dnf install android-tools
```

### macOS

```bash
brew install --cask android-platform-tools
```

### Windows

1. Tải `platform-tools-latest-windows.zip` từ:
   - https://developer.android.com/tools/releases/platform-tools

2. Giải nén vào (ví dụ) `C:\platform-tools\`

3. **Cách A - Thêm vào PATH:**
   - Mở **System Properties** → **Environment Variables** → **Path** → **Edit**
   - Click **New** và thêm `C:\platform-tools`
   - Click OK, mở PowerShell mới

4. **Cách B - Set biến `ADB_PATH`:**
   ```powershell
   setx ADB_PATH "C:\platform-tools\adb.exe"
   ```

### Xác minh cài đặt

```bash
# Kiểm tra version
adb version       # phải in "Android Debug Bridge version 1.0.x"

# Liệt kê thiết bị
adb devices       # cắm USB + nhấn "Allow" trên điện thoại
```

> **Lần đầu kết nối USB**, điện thoại sẽ hỏi **"Allow USB debugging from this computer?"** — nhấn **Allow**, có thể tick **Always allow from this computer**. Nếu không thấy dialog, kiểm tra USB cable (phải là data cable, không phải charge-only).

**Nếu ADB không trong PATH của user chạy server** (thường gặp khi chạy qua `systemd`):
```bash
export ADB_PATH=/usr/bin/adb
```

---

## 📦 Cài đặt nhanh

### 1️⃣ Clone & setup dependencies

```bash
git clone https://github.com/nhoxboo/web-scrcpy-fresh-private.git
cd web-scrcpy-fresh-private

# Cài đặt dependencies tối thiểu (backend)
pip install -r requirements.txt

# Cài đặt và build giao diện (frontend)
cd frontend
npm install
npm run build
cd ..
```

### 2️⃣ Development setup (optional)

```bash
# Cài đặt dev tools + testing
pip install -r requirements-dev.txt

# Thiết lập pre-commit hooks
pre-commit install

# Chạy tests
pytest

# Format & lint
ruff check . && ruff format --check .
```

### 3️⃣ Production setup (optional)

```bash
# Cài đặt gunicorn + eventlet
pip install -r requirements-prod.txt
```

---

## 🚀 Hướng dẫn chạy

### ⚠️ QUAN TRỌNG: Development vs Production

| Chế độ | Dùng cho | Command | Lưu ý |
|-------|---------|---------|-------|
| **Werkzeug** | Dev/Test local | `python app.py` | Single-threaded, video stream stutter nếu nhiều user |
| **gunicorn + eventlet** | Production | `gunicorn --worker-class eventlet -w 1 ...` | ✅ Multi-client, smooth stream |

### Development mode (Werkzeug)

```bash
python app.py --port 8000
```

App sẽ in cảnh báo:
```
!!! Đang chạy Werkzeug development server - KHÔNG dùng cho production !!!
```

Set `DISABLE_DEV_BANNER=1` để ẩn cảnh báo nếu dev local có chủ ý:
```bash
DISABLE_DEV_BANNER=1 python app.py
```

### Production mode (gunicorn + eventlet) — KHUYẾN NGHỊ

#### Option 1: Direct gunicorn

```bash
pip install -r requirements-prod.txt

# Generate secret key
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# Chạy (1 worker bắt buộc)
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 wsgi:app
```

#### Option 2: Dùng honcho (read Procfile)

```bash
pip install honcho
honcho start
```

> **⚠️ BẮTER 1 WORKER**: State scrcpy session là per-process. Nhiều worker sẽ tranh nhau device. Để scale, đặt sau reverse proxy (nginx/Caddy) và lock device per container.

### HTTPS & Reverse proxy (khuyến nghị nếu public)

Nhiều API browser cần **secure context (HTTPS)**:
- `navigator.clipboard.*` chỉ hoạt động trên HTTPS
- Pointer Lock yêu cầu HTTPS trên Chrome strict mode

#### Caddy (tự động HTTPS)

```caddyfile
# /etc/caddy/Caddyfile
remote.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl reload caddy
```

Trước khi chạy app, set:
```bash
export SESSION_COOKIE_SECURE=1   # Cookie chỉ gửi qua HTTPS
export PROXY_FIX_X_FOR=1         # Trust X-Forwarded-* từ Caddy
gunicorn --worker-class eventlet -w 1 --bind 127.0.0.1:8000 wsgi:app
```

#### nginx + Let's Encrypt (Ubuntu)

```nginx
server {
    listen 443 ssl http2;
    server_name remote.example.com;
    
    ssl_certificate     /etc/letsencrypt/live/remote.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/remote.example.com/privkey.pem;

    # WebSocket headers cho Socket.IO
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600;
    }
}
```

```bash
sudo certbot --nginx -d remote.example.com
```

---

## 📁 Cấu trúc dự án

```
web-scrcpy-fresh-private/
├── app.py                          # Entry point chính (Flask app)
├── wsgi.py                         # WSGI entry point (gunicorn)
├── scrcpy.py                       # Logic tích hợp scrcpy + ADB commands
├── reset_password.py               # CLI reset password nếu quên
├── scrcpy-server                   # Binary scrcpy-server (Android side)
├── Procfile                        # Heroku-style production command
├── pyproject.toml                  # Project metadata
├── requirements.txt                # Core dependencies
├── requirements-prod.txt           # Production deps (gunicorn, eventlet)
├── requirements-dev.txt            # Dev deps (pytest, ruff, pre-commit)
├── .env.example                    # Example environment variables
├── .gitignore                      # Git ignore rules
├── .pre-commit-config.yaml         # Pre-commit hooks config
│
├── templates/                      # HTML templates
│   ├── index.html                  # Main control interface
│   ├── login.html                  # Login page
│   ├── change_password.html        # Password change page
│   └── ...
│
├── static/                         # Static assets (JS, CSS, fonts)
│   ├── js/
│   │   ├── main.js                 # Main client-side logic
│   │   ├── video-stream.js         # Video streaming logic
│   │   ├── touch-handler.js        # Multi-touch gesture handling
│   │   └── ...
│   ├── css/
│   │   ├── style.css               # Main styles
│   │   └── ...
│   └── fonts/
│
├── tests/                          # Unit & integration tests
│   ├── test_app.py
│   ├── test_scrcpy.py
│   └── ...
│
└── .github/                        # GitHub Actions workflows (CI/CD)
    └── workflows/
```

### File chính

| File | Mục đích |
|------|---------|
| **app.py** | Flask server, routes chính, WebSocket handling, authentication |
| **scrcpy.py** | ADB + scrcpy binary integration, video streaming, device control |
| **reset_password.py** | CLI để reset password khi quên |
| **wsgi.py** | WSGI application wrapper cho gunicorn |

### Thư mục templates

- `index.html` — Giao diện chính với canvas, controls, settings
- `login.html` — Form đăng nhập
- `change_password.html` — Form đổi mật khẩu

### Thư mục static

- `js/main.js` — Logic client chính (kết nối WebSocket, event listeners)
- `js/video-stream.js` — Xử lý H.264 video decoding, canvas rendering
- `js/touch-handler.js` — Multi-touch gesture recognition & ADB input
- `css/style.css` — Styling cho responsive UI

---

## 🤝 Hướng dẫn đóng góp

Chúng mình hoan nghênh pull requests từ cộng đồng! Vui lòng tuân theo quy trình này.

### 1️⃣ Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/web-scrcpy-fresh-private.git
cd web-scrcpy-fresh-private
git checkout -b feature/your-feature-name
```

### 2️⃣ Thiết lập development environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements-dev.txt
pre-commit install
```

### 3️⃣ Code style & Linting

Project sử dụng **ruff** cho format & lint:

```bash
# Format code
ruff format .

# Check issues
ruff check .

# Hoặc pre-commit sẽ chạy auto trước khi commit
git add .
git commit -m "feat: your changes"  # Pre-commit hooks chạy auto
```

### 4️⃣ Testing

```bash
pytest                    # Chạy tất cả tests
pytest -v                 # Verbose mode
pytest -k test_name       # Chạy test cụ thể
```

### 5️⃣ Commit message convention

Theo [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: thêm multi-touch support
fix: sửa bug video stream stutter
docs: update README
refactor: clean up scrcpy.py code
test: thêm unit test cho authentication
```

### 6️⃣ Push & create Pull Request

```bash
git push origin feature/your-feature-name
```

Rồi tạo PR trên GitHub:
- **Title**: ngắn gọn, mô tả feature/fix
- **Description**: chi tiết về thay đổi, why, cách test
- **Linked issues**: nếu fix issue #123, viết `Closes #123`

### Quy tắc review

- ✅ Code phải pass `ruff check` và `ruff format`
- ✅ Unit tests phải pass (`pytest`)
- ✅ Không thêm dependencies mới mà chưa discuss
- ✅ Update docs / README nếu có breaking changes
- ✅ Commit message phải rõ ràng

---

## ⚙️ Tinh chỉnh hiệu suất

### Video stream quality

Default đã tune cho **LAN / Wi-Fi 5+ flagship devices**:

```bash
SCRCPY_VIDEO_BIT_RATE=10000000  # 10 Mbps
SCRCPY_MAX_FPS=60               # 60 FPS
SCRCPY_MAX_SIZE=1920            # Cap longest edge
```

### Gợi ý điều chỉnh

| Kịch bản | Bitrate | Max size | Max FPS | Lý do |
|---------|---------|----------|---------|-------|
| LAN gigabit, flagship phone | 15 Mbps | 1920 | 60 | Băng thông dồi dào |
| Wi-Fi 5+ (mặc định) | 10 Mbps | 1920 | 60 | Balance |
| Wi-Fi yếu / 3G VN | 6 Mbps | 1280 | 30 | Tiết kiệm băng thông |
| 4G/LTE, mạng quốc tế | 3 Mbps | 1080 | 30 | Constraint tối đa |

### Cách đặt

```bash
# Inline
export SCRCPY_VIDEO_BIT_RATE=15000000
export SCRCPY_MAX_SIZE=1920
export SCRCPY_MAX_FPS=60
python app.py

# Hoặc qua .env file
cat .env.example > .env
# Edit .env với các giá trị mới
```

### Stream HUD (FPS/Mbps monitor)

Mở DevTools → Console:
```javascript
localStorage.setItem('streamHud', '1')
```

Hoặc bấm **Ctrl+Shift+H** trong tab để toggle HUD góc màn hình → hiển thị FPS, Mbps thực tế, tổng frame.

---

## 🔒 Bảo mật

### Default credentials

Lần chạy đầu, tạo tài khoản mặc định:
- Username: `admin`
- Password: `admin123` (đã hash trong `auth.json`)

**⚠️ Đổi mật khẩu ngay sau khi deploy!**

### Bảo mật best practices

1. **Không public lên Internet nếu chưa sẵn sàng:**
   - Không có reverse proxy + auth bổ sung
   - Không có HTTPS
   - Không có VPN / firewall

2. **Đổi default password:**
   ```bash
   python reset_password.py --username admin
   ```

3. **Set `FLASK_SECRET_KEY`:**
   ```bash
   export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```
   (Không commit `secret.key` local)

4. **HTTPS + reverse proxy:**
   - Dùng Caddy hoặc nginx với Let's Encrypt
   - Set `SESSION_COOKIE_SECURE=1` trước chạy app

5. **Không commit nhạy cảm:**
   - `auth.json` — đã `.gitignore`
   - `secret.key` — đã `.gitignore`
   - `.env` — dùng `.env.example` template

6. **Audio disabled:**
   - Scrcpy-server chạy với `audio=false` (mặc định) để giảm băng thông
   - Có thể enable qua `scrcpy.py` nếu cần

### Monitoring & Health check

Endpoint `/healthz` (không cần login):
```bash
curl http://localhost:8000/healthz
# {"status": "ok", "has_client": false}
```

Dùng cho load balancer / uptime monitor.

---

## 🐛 Troubleshooting

### Device không hiển thị

**Triệu chứng:** `adb devices` không liệt kê phone

**Giải pháp:**
1. Kiểm tra USB Debugging đã bật trên phone
2. Kiểm tra cable (phải là data cable, không charge-only)
3. Chạy lại `adb kill-server && adb devices`
4. Kiểm tra ADB version: `adb version`

### Giao diện chỉ hiện hình nền (không có nút bấm/video)

**Triệu chứng:** Mở trang web chỉ thấy hình nền (background), không thấy giao diện UI để thao tác.

**Giải pháp:**
Giao diện React ở thư mục `frontend` chưa được build ra thư mục `static/dist`. Hãy chạy các lệnh sau để build giao diện:
```bash
cd frontend
npm install
npm run build
cd ..
```

### Port 8000 đã bị dùng

**Triệu chứng:** `Address already in use`

**Giải pháp:**
```bash
# Tìm process chiếm port
lsof -i :8000        # macOS/Linux
netstat -ano | grep :8000  # Windows

# Dùng port khác
python app.py --port 8001
```

### Video stream không hoạt động

**Triệu chứng:** Màn hình đen hoặc "Connection lost"

**Giải pháp:**
1. Kiểm tra ADB kết nối: `adb shell echo "ok"`
2. Kiểm tra USB/Wi-Fi ổn định
3. Kiểm tra Werkzeug (dev) vs gunicorn (prod) — gunicorn mượt hơn
4. Xem logs app: `FLASK_DEBUG=1 python app.py`

### Mật khẩu quên

**Giải pháp:**
```bash
# Interactive
python reset_password.py --username admin

# Non-interactive
python reset_password.py --non-interactive --username admin --password 'new_password'
```

Khởi động lại app sau reset.

### Multi-touch không hoạt động

**Triệu chứng:** Pinch-to-zoom không responsive

**Giải pháp:**
1. Kiểm tra browser hỗ trợ Pointer Events (`navigator.pointerEvents`)
2. Update Chrome/Firefox/Safari lên version mới
3. Inspect `console.log` browser DevTools xem event có fire không

### HTTPS certificate error

**Triệu chứng:** Browser cảnh báo "Untrusted certificate"

**Giải pháp:**
1. Dùng Let's Encrypt (free, tự động) via Caddy/certbot
2. Hoặc self-signed certificate cho internal use (tạm thời)

---

## 📝 Environment variables

Chi tiết trong `.env.example`, copy ra `.env` để tùy chỉnh:

```bash
# Server
FLASK_DEBUG=0                          # Bật/tắt debug mode
FLASK_SECRET_KEY=...                   # Secret key cho session
SESSION_COOKIE_SECURE=1                # Cookie chỉ qua HTTPS
PROXY_FIX_X_FOR=1                      # Trust X-Forwarded-* từ proxy

# Video stream
SCRCPY_VIDEO_BIT_RATE=10000000        # Bitrate (bps)
SCRCPY_MAX_FPS=60                      # Max FPS
SCRCPY_MAX_SIZE=1920                   # Max resolution (longest edge)

# ADB
ADB_PATH=/usr/bin/adb                 # Đường dẫn adb (nếu không trong PATH)

# UI
DISABLE_DEV_BANNER=1                   # Ẩn warning Werkzeug development
```

---

## 📚 Resources

- [scrcpy project](https://github.com/Genymobile/scrcpy) — Original project
- [Android Debug Bridge](https://developer.android.com/tools/adb) — Official ADB docs
- [Flask documentation](https://flask.palletsprojects.com/) — Web framework
- [python-socketio](https://python-socketio.readthedocs.io/) — Real-time communication

---

## 📄 License

Apache License 2.0 — Xem [LICENSE.txt](./LICENSE.txt)

Dự án này kế thừa license từ scrcpy gốc.

---

## 💡 Tương lai roadmap

- [ ] Multi-device support (control nhiều phone đồng thời)
- [ ] Screen mirroring qua Chromecast
- [ ] Advanced gesture recording & playback
- [ ] Performance profiling dashboard
- [ ] Integration với CI/CD (app testing automation)
- [ ] Mobile app client (iOS/Android)

---

## 🆘 Support & Contact

- 📧 Issues: [GitHub Issues](https://github.com/nhoxboo/web-scrcpy-fresh-private/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/nhoxboo/web-scrcpy-fresh-private/discussions)

---

**Happy hacking! 🚀**
