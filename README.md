# Web Scrcpy Fresh (Private Build)

Bản private dùng nội bộ để điều khiển thiết bị Android qua trình duyệt web (dựa trên `scrcpy`).

## Tính năng chính
- Điều khiển Android từ browser qua giao diện web
- Hỗ trợ thao tác chuột/bàn phím cơ bản
- Có trang đăng nhập và đổi mật khẩu
- Dễ chạy local trong mạng nội bộ

## Yêu cầu hệ thống
- Windows/macOS/Linux
- Python **3.7+**
- `adb` đã cài và có trong PATH
- Thiết bị Android đã bật **USB Debugging**

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

### Dev (Werkzeug)
```bash
python app.py --port 8000
```

### Production (gunicorn + eventlet)
```bash
pip install -r requirements-prod.txt
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export SESSION_COOKIE_SECURE=1   # chỉ bật khi đứng sau HTTPS
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 wsgi:app
```

> **Bắt buộc 1 worker.** State scrcpy session là process-local; nhiều worker sẽ tranh nhau device. Để scale, đặt sau reverse proxy (nginx/Caddy) và lock device theo từng container.

Mở trình duyệt tại:
- `http://localhost:8000`

### Quên mật khẩu?
Dừng app rồi chạy:
```bash
python reset_password.py --username admin
# hoặc không tương tác: python reset_password.py --non-interactive --username admin --password '<mới>'
```
Script sẽ ghi đè `auth.json` với mật khẩu mới (đã hash). Khởi động lại app sau khi reset.

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
