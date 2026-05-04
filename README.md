# Web Scrcpy Fresh (Private Build)

Bản private dùng nội bộ để điều khiển thiết bị Android qua trình duyệt web (dựa trên `scrcpy`).

## Tính năng chính
- Điều khiển Android từ browser qua giao diện web
- Hỗ trợ thao tác chuột/bàn phím cơ bản
- **Multi-touch** qua Pointer Events (pinch-to-zoom, 2-3 ngón)
- Fullscreen mượt (video scale 100vw x 100vh)
- **Chụp ảnh / quay video** màn hình thiết bị (Ctrl+Shift+S / Ctrl+Shift+R)
- Có trang đăng nhập và đổi mật khẩu
- Dễ chạy local trong mạng nội bộ

## Yêu cầu hệ thống
- Windows/macOS/Linux
- Python **3.10+** (khớp matrix CI: 3.10 / 3.11 / 3.12)
- `adb` đã cài và có trong PATH (xem [Cài đặt ADB](#cài-đặt-adb-bắt-buộc))
- Thiết bị Android đã bật **USB Debugging**

## Cài đặt ADB (bắt buộc)
Server cần `adb` để nói chuyện với thiết bị Android. Nếu lệnh `adb version`
trên máy báo "command not found" thì server sẽ start được nhưng socket sẽ
ngay lập tức trả lỗi `Không thể khởi động scrcpy`.

### Linux
```bash
# Debian / Ubuntu / Linux Mint
sudo apt update && sudo apt install -y android-tools-adb

# Arch / Manjaro
sudo pacman -S android-tools

# Fedora / RHEL
sudo dnf install android-tools
```

### macOS
```bash
brew install --cask android-platform-tools
```

### Windows
1. Tải `platform-tools-latest-windows.zip` từ
   <https://developer.android.com/tools/releases/platform-tools>.
2. Giải nén ra (ví dụ) `C:\platform-tools\`.
3. Mở **System Properties → Environment Variables → Path → Edit → New** và
   thêm đường dẫn đó. Hoặc set biến môi trường `ADB_PATH` trỏ thẳng tới
   `adb.exe`:
   ```powershell
   setx ADB_PATH "C:\platform-tools\adb.exe"
   ```
4. Mở 1 PowerShell mới và xác nhận `adb version`.

### Verify
```bash
adb version       # phải in "Android Debug Bridge version 1.0.x"
adb devices       # cắm USB + accept dialog "Allow USB debugging" trên máy
```

> Lần đầu cắm USB, điện thoại sẽ hỏi **"Allow USB debugging from this
> computer?"** — nhấn **Allow**, có thể tick **Always allow**. Nếu không thấy
> dialog, kiểm tra lại USB cable (cần cable hỗ trợ data, không phải charge-only).

Nếu adb đã cài nhưng không nằm trong `PATH` của user chạy server (thường gặp
khi chạy qua `systemd` hoặc service), set `ADB_PATH` trong env:
```bash
export ADB_PATH=/usr/bin/adb
```

## Cài đặt nhanh
```bash
pip install -r requirements.txt
```

### Dev / test
```bash
pip install -r requirements-dev.txt
pre-commit install
pytest
ruff check . && ruff format --check .
```

## Cách chạy

> ⚠️ **QUAN TRỌNG**: chỉ dùng Werkzeug (`python app.py`) khi dev/test trên
> máy local. Production **bắt buộc** chạy `gunicorn` để stream video mượt —
> Werkzeug single-threaded sẽ stutter khi có user kết nối thực tế.
> Nếu bạn đang chạy `python app.py` trên server public, header HTTP sẽ
> trả `Server: Werkzeug/...` — đó là dấu hiệu cần chuyển sang gunicorn.

### Triển khai production — Docker (DỄ NHẤT)
1 lệnh là chạy được, có sẵn gunicorn + adb + healthcheck + persistent volume:
```bash
cp .env.example .env
echo "FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
docker compose up -d
docker compose logs -f
```
- App available tại http://localhost:8000 (đăng nhập lần đầu: `admin` / `admin123` → đổi mật khẩu ngay)
- `auth.json` / `secret.key` / `audit.log` lưu trong named volume `webscrcpy-data` (persist qua `docker compose down`)
- USB thiết bị: mặc định bind `/dev/bus/usb` + `privileged: true` (Linux). Trên Windows/macOS hãy dùng **Wireless ADB** (form "Pair via Wi-Fi" trên trang `/devices`) và gỡ 2 dòng đó trong `docker-compose.yml`.

```bash
# Build lại sau khi đổi code
docker compose build --no-cache
docker compose up -d

# Reset mật khẩu (chạy reset_password.py bên trong container)
docker compose exec web python reset_password.py --username admin

# Stop + xoá tất cả (state vẫn còn nhờ volume)
docker compose down

# Stop + xoá luôn volume (mất auth + audit log!)
docker compose down -v
```

### Triển khai production (gunicorn + eventlet, không Docker)
```bash
pip install -r requirements-prod.txt
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export SESSION_COOKIE_SECURE=1   # chỉ bật khi đứng sau HTTPS
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 wsgi:app
```

Hoặc dùng `honcho` (đọc `Procfile` có sẵn):
```bash
pip install honcho
honcho start
```

> **Bắt buộc 1 worker.** State scrcpy session là process-local; nhiều worker sẽ tranh nhau device. Để scale, đặt sau reverse proxy (nginx/Caddy) và lock device theo từng container.

### Dev / debug (Werkzeug, KHÔNG dùng cho production)
```bash
python app.py --port 8000
```

App sẽ in cảnh báo `!!! Đang chạy Werkzeug development server ...` — đó là
bản thân code nhắc bạn chuyển sang gunicorn. Set `DISABLE_DEV_BANNER=1` để
ẩn cảnh báo nếu bạn cố ý dev local.

### Tinh chỉnh chất lượng / mượt video

Default đã được tune cho LAN / Wi-Fi 5+ trên flagship hiện đại:
- `SCRCPY_VIDEO_BIT_RATE=10000000` (10 Mbps)
- `SCRCPY_MAX_FPS=60`
- `SCRCPY_MAX_SIZE=1920` (cap longest edge — mượt + nét hơn so với native
  trên phone 4K vì cùng bitrate được trải lên ít pixel hơn)

Gợi ý điều chỉnh theo môi trường:

| Tình huống | Bit rate | max_size | max_fps |
|---|---|---|---|
| LAN gigabit, phone flagship | 15 000 000 | 1920 | 60 |
| Wi-Fi 5+ thông thường (mặc định) | 10 000 000 | 1920 | 60 |
| Wi-Fi yếu / mạng nhà mạng VN | 6 000 000 | 1280 | 30 |
| 4G/LTE / mạng quốc tế | 3 000 000 | 1080 | 30 |

Đặt qua env var (`.env` hoặc inline):
```bash
export SCRCPY_VIDEO_BIT_RATE=15000000
export SCRCPY_MAX_SIZE=1920
export SCRCPY_MAX_FPS=60
```

Mở DevTools → Console rồi gõ `localStorage.setItem('streamHud','1')` (hoặc
bấm **Ctrl+Shift+H** trong tab) để bật HUD góc màn hình hiển thị FPS / Mbps
/ tổng số frame thực tế — dùng để verify thay đổi env có ăn không.

Mở trình duyệt tại:
- `http://localhost:8000`

### Quên mật khẩu?
Dừng app rồi chạy:
```bash
python reset_password.py --username admin
# hoặc không tương tác: python reset_password.py --non-interactive --username admin --password '<mới>'
```
Script sẽ ghi đè `auth.json` với mật khẩu mới (đã hash). Khởi động lại app sau khi reset.

### HTTPS / reverse proxy (khuyến nghị nếu mở ra Internet)
Trang `http://...:8000` chạy được nhưng nhiều API browser yêu cầu **secure
context (HTTPS hoặc localhost)**:
- `navigator.clipboard.readText / writeText` (đồng bộ clipboard 2 chiều) chỉ
  hoạt động trên HTTPS — trên domain HTTP sẽ silent fail.
- Pointer Lock (UHID mouse) cũng yêu cầu HTTPS trong Chrome strict mode.

Cách nhanh nhất là đặt **Caddy** đứng trước, nó tự lo Let's Encrypt:
```caddyfile
# /etc/caddy/Caddyfile
remote.example.com {
    reverse_proxy 127.0.0.1:8000
}
```
```bash
sudo systemctl reload caddy
```
Caddy sẽ tự xin cert cho `remote.example.com` (cần DNS A record trỏ về VPS).
Sau đó set thêm 2 env trước khi chạy app:
```bash
export SESSION_COOKIE_SECURE=1   # cookie chỉ gửi qua HTTPS
export PROXY_FIX_X_FOR=1         # ProxyFix tin X-Forwarded-* từ Caddy
```

Hoặc với **nginx + certbot** (Ubuntu):
```nginx
server {
    listen 443 ssl http2;
    server_name remote.example.com;
    ssl_certificate     /etc/letsencrypt/live/remote.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/remote.example.com/privkey.pem;

    # WebSocket cần Upgrade headers cho Socket.IO
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

### Health check
`GET /healthz` trả về JSON `{"status":"ok","has_client":<bool>}` — không cần đăng nhập, dùng cho load balancer / uptime monitor.

## Quy trình kết nối thiết bị
1. Cắm điện thoại vào máy (hoặc kết nối ADB qua Wi-Fi)
2. Chấp nhận quyền USB Debugging trên điện thoại
3. Kiểm tra thiết bị:
   ```bash
   adb devices
   ```
4. Mở web UI và bắt đầu điều khiển

## Cấu trúc thư mục chính
- `app.py`: entrypoint server (dev mode `python app.py`)
- `wsgi.py`: WSGI entrypoint cho gunicorn (`gunicorn ... wsgi:app`)
- `scrcpy.py`: logic tích hợp scrcpy
- `reset_password.py`: CLI reset credentials nếu quên mật khẩu
- `templates/`: giao diện HTML
- `static/`: JS/CSS/fonts
- `requirements.txt`: dependencies tối thiểu để chạy
- `requirements-prod.txt`: thêm gunicorn + eventlet để chạy production
- `requirements-dev.txt`: thêm pytest + ruff + pre-commit để dev/test
- `Procfile`: command production (Heroku-style platforms)

## Bảo mật (quan trọng)
Vì đây là bản private, nên khuyến nghị:
- Không public cổng ra Internet nếu chưa có reverse proxy + auth bổ sung
- Đổi mật khẩu mặc định ngay khi deploy (tài khoản mặc định `admin/admin123` sẽ được tạo lần đầu chạy với mật khẩu đã hash)
- Đặt `FLASK_SECRET_KEY` qua env var thay vì dùng file `secret.key` local nếu triển khai nhiều node
- Không commit thông tin nhạy cảm (`auth.json`, `secret.key`, `.env` đều đã được `.gitignore`)
- Audio stream đã tắt mặc định ở scrcpy-server (`audio=false`) để giảm băng thông

## Troubleshooting nhanh
- Không thấy device: kiểm tra lại `adb devices` và USB Debugging
- Port bận: đổi port chạy app hoặc tắt tiến trình đang chiếm cổng
- Không stream được: kiểm tra cáp USB/chế độ kết nối và quyền ADB

## License
Kế thừa Apache License 2.0 từ dự án gốc.
