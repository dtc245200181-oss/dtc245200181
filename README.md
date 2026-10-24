# Hệ thống quản lý thư viện (Đề 1)

Flask + PostgreSQL + pgAdmin + Nginx (HTTPS) chạy bằng Docker Compose.

## Chạy hệ thống
cp .env.example .env   # điền mật khẩu mạnh
# sinh chứng chỉ tự ký bằng openssl vào nginx/certs/
docker compose up -d --build
