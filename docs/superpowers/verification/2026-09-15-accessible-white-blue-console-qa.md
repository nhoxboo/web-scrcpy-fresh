# Báo cáo QA cô lập — console trắng-xanh dễ tiếp cận

## Phạm vi và ranh giới

Báo cáo này ghi nhận QA cô lập tại commit `805cbad` (`fix: link SVG favicon from production templates`) trên nhánh `feature/accessibility-ui-redesign`. Chỉ tài liệu này được tạo cho Task 5; không có thay đổi mã hành vi production.

- Listener QA riêng chạy ở cổng `8010`, với `DISABLE_ADB_KEEPALIVE=1`; log xác nhận: `ADB keep-alive loop is disabled`.
- Cổng production `8000` được quan sát đang lắng nghe bởi PID `10728`, nhưng **không** bị khởi động lại hay tác động.
- Instance QA và tiến trình Chrome CDP cô lập đã được dừng rõ ràng sau QA.
- `saved_wifi_devices.json` không được sửa hoặc stage bởi công việc này.

## Ma trận xác minh

| Hạng mục | Lệnh / bối cảnh | Kết quả quan sát |
|---|---|---|
| Bộ kiểm thử đầy đủ | `python -m pytest -q` | `223 passed, 1 EventletDeprecationWarning` |
| Lint | `python -m ruff check .` | `all checks passed` |
| Định dạng | `python -m ruff format --check .` | `42 files already formatted` |
| Khoảng trắng diff | `git diff --check` | clean |
| Listener QA | `DISABLE_ADB_KEEPALIVE=1 ... app.py --port 8010` | Lắng nghe tại `8010` trước khi dọn dẹp; log xác nhận keep-alive ADB bị tắt |
| Điều hướng chưa xác thực | Yêu cầu tới listener `8010` | `/login` = `200`; `/devices`, `/ios`, `/` = `302` tới `/login` đúng như kỳ vọng |
| Favicon sau khắc phục | `GET /static/dist/favicon.svg` trên listener QA | `200` |
| Production | Quan sát cổng `8000` | PID `10728` đang lắng nghe; không restart, không kiểm tra health, không triển khai |

## QA trình duyệt cô lập

Chrome CDP được kiểm tra tại các viewport emulated thực tế sau trên `/login`:

| Viewport | Không tràn ngang | Nhãn và nội dung | Kích thước điều khiển | Kiểm tra trực quan |
|---|---|---|---|---|
| `375x812` | `document/body scrollWidth == clientWidth` | Có `Tên đăng nhập`, `Mật khẩu`; mô tả được giữ nguyên | Input/nút tương tác tối thiểu `44px` | Không clipping/chồng lấp; nhãn hiện rõ, tương phản dễ đọc |
| `768x1024` | `document/body scrollWidth == clientWidth` | Có nhãn và mô tả | Input/nút tương tác tối thiểu `44px` | Kiểm tra cấu trúc qua CDP |
| `1024x768` | `document/body scrollWidth == clientWidth` | Có nhãn và mô tả | Input/nút tương tác tối thiểu `44px` | Kiểm tra cấu trúc qua CDP |
| `1440x900` | `document/body scrollWidth == clientWidth` | Có `Tên đăng nhập`, `Mật khẩu`; mô tả được giữ nguyên | Input/nút tương tác tối thiểu `44px` | Không clipping/chồng lấp; nhãn hiện rõ, tương phản dễ đọc |

Chrome CDP không ghi nhận Runtime JavaScript exception. Trước khi sửa favicon, chỉ có phát hiện mạng trong console là `favicon.ico` trả `404`. Vấn đề này đã được khắc phục: SVG canonical `/static/dist/favicon.svg` trả `200`, và kiểm thử link bảo vệ tất cả template production. Không có tuyên bố về một lần chụp console CDP hậu-sửa favicon.

## Giới hạn đã biết

- Các route Android console, `/devices` và `/ios` được bảo vệ không được xác thực hay thực hiện action; chỉ xác nhận redirect khi chưa xác thực.
- Không có Android/iOS vật lý, ADB hoặc điều khiển Scrcpy nào được sử dụng, vì migration giao diện không được phát sinh device action.
- Phủ tĩnh binding/contract dựa trên full test suite; đây không phải smoke test thiết bị đã xác thực.
- Không có PR, CI, merge hoặc production restart trong Task 5 này.

## Quyết định phát hành

**GO cho final code review và PR CI trên nhánh mã.** Production rollout vẫn **pending** merge, CI xanh và phê duyệt người dùng; không được suy diễn rằng production đã được triển khai hoặc khởi động lại.
