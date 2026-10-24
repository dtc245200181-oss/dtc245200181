# Hệ thống quản lý thư viện – Đề 1

Đồ án học phần **Triển khai và Quản trị Hệ thống Phần mềm**.
Sinh viên: Trieu Kim Thoa – MSSV: dtc245200181

Ứng dụng web quản lý thư viện (sách, độc giả, mượn/trả) viết bằng Flask, dùng
PostgreSQL, chạy hoàn toàn bằng Docker Compose cùng hệ thống giám sát và log tập trung.

## Kiến trúc

Trình duyệt ──HTTPS 443──> Nginx ──> Flask (gunicorn) ──> PostgreSQL <── pgAdmin
│ │ /metrics │
│ stub_status│ │ pg_monitor
nginx-exporter Prometheus <── postgres-exporter
│ ^──── cAdvisor (container)
Grafana ──> Loki <── Promtail <── docker logs


| Service | Vai trò | Cổng ngoài |
|---|---|---|
| nginx | Reverse proxy, HTTPS tự ký, security headers | 80, 443 |
| app | Ứng dụng Flask + gunicorn (user không phải root) | không |
| db | PostgreSQL 16 | không |
| pgadmin | Công cụ quản trị DB | 5050 |
| prometheus | Thu thập metrics | 9090 |
| grafana | Dashboard và truy vấn log | 3000 |
| cadvisor, nginx-exporter, postgres-exporter | Exporter cho container, web server, database | không |
| loki, promtail | Log tập trung | không |

Mạng: `frontend` (nginx, app, pgadmin), `backend` (db, app, pgadmin, postgres-exporter,
cách ly hoàn toàn – `internal`), `monitoring` (giám sát và log).

## Yêu cầu

Ubuntu có Docker và Docker Compose v2, Git, OpenSSL.

## Hướng dẫn chạy

```bash
git clone https://github.com/dtc245200181-oss/dtc245200181.git
cd dtc245200181

# 1. Tạo file biến môi trường, điền mật khẩu mạnh (ví dụ: openssl rand -hex 16)
cp .env.example .env
nano .env

# 2. Sinh chứng chỉ HTTPS tự ký (thay <IP> bằng IP máy chạy hệ thống)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/selfsigned.key -out nginx/certs/selfsigned.crt \
  -subj "/CN=<IP>" -addext "subjectAltName=IP:<IP>"
chmod 644 nginx/certs/selfsigned.key

# 3. Khởi động
docker compose up -d --build
docker compose ps
```

## Địa chỉ truy cập

| Dịch vụ | URL |
|---|---|
| Website thư viện | https://<IP> (trình duyệt cảnh báo chứng chỉ tự ký, chọn tiếp tục) |
| pgAdmin | http://<IP>:5050 (server: host `db`, port `5432`) |
| Prometheus | http://<IP>:9090 |
| Grafana | http://<IP>:3000 (user `admin`, mật khẩu `GRAFANA_ADMIN_PASSWORD`) |

## Giám sát

Prometheus thu thập từ cAdvisor, nginx-exporter, postgres-exporter và `/metrics` của app.
Dashboard Grafana (import theo ID): cAdvisor `14282`, NGINX `12708`, PostgreSQL `9628`,
cùng dashboard tự tạo `Library App` (request/giây, độ trễ p95, trạng thái service).

## Log tập trung và truy vấn LogQL

Promtail đọc log mọi container qua Docker socket, đẩy vào Loki. Truy vấn trong Grafana → Explore → Loki:

```logql
{service="nginx"}
{service="nginx"} |= " 404 "
{service="nginx"} |~ " (4|5)[0-9]{2} "
{service="db"} |= "ERROR"
sum by (service) (count_over_time({service=~".+"}[5m]))
```

## Hardening

- App chạy bằng user không phải root (uid 10001); Nginx dùng image `nginx-unprivileged`.
- Database nằm trong mạng `internal`, không publish cổng 5432.
- Mật khẩu ngẫu nhiên lưu trong `.env` (không commit, đã có trong `.gitignore`).
- Nginx: HTTPS (TLS 1.2/1.3), chuyển HTTP sang HTTPS, ẩn phiên bản, các header
  `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`,
  `Content-Security-Policy`, `Strict-Transport-Security`; `/metrics` bị chặn từ ngoài.
- Phân quyền DB tối thiểu: app chỉ có SELECT/INSERT/UPDATE/DELETE; user giám sát chỉ có `pg_monitor`.
- Container: `cap_drop: ALL`, `no-new-privileges`, filesystem chỉ đọc cho app,
  giới hạn RAM và số tiến trình, giới hạn dung lượng log.
- Ngoại lệ: cAdvisor và Promtail cần đọc dữ liệu hệ thống/`docker.sock` (chỉ đọc).

## Cấu trúc thư mục
