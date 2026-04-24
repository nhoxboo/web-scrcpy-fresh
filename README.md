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
```bash
python app.py
```

Mở trình duyệt tại:
- `http://localhost:5000`

## Quy trình kết nối thiết bị
1. Cắm điện thoại vào máy (hoặc kết nối ADB qua Wi-Fi)
2. Chấp nhận quyền USB Debugging trên điện thoại
3. Kiểm tra thiết bị:
   ```bash
   adb devices
   ```
4. Mở web UI và bắt đầu điều khiển

## Cấu trúc thư mục chính
- `app.py`: entrypoint server
- `scrcpy.py`: logic tích hợp scrcpy
- `templates/`: giao diện HTML
- `static/`: JS/CSS/fonts
- `requirements.txt`: dependencies Python

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
