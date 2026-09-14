# Runtime TLS files

Không đặt private key hoặc chứng chỉ production vào thư mục này.

Dùng TLS do reverse proxy/certificate manager quản lý, hoặc cấu hình HTTPS launcher trỏ tới đường dẫn runtime nằm ngoài repository. Runtime certificate files chỉ được service identity đọc và tuyệt đối không commit vào Git.
