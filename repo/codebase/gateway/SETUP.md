# Gateway setup

Chạy từ thư mục `repo/` với Python 3.11–3.13:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e codebase/ml
.venv/bin/pip install -e 'codebase/gateway[dev]'
```

Khởi động Training API (`:8001`), Intel (`:8002`) và Detection (`:8003`)
trước Gateway. Sao chép `codebase/gateway/.env.example` và cấu hình các URL/key
nội bộ, sau đó:

```bash
.venv/bin/chan-gateway
curl --fail http://127.0.0.1:8000/healthz
curl --fail http://127.0.0.1:8000/readyz
```

Gateway vẫn cần PostgreSQL cho device token, analysis metadata và feedback,
nhưng DB role của nó không cần quyền trên training hay threat-intel tables.

Importer blocklist cũ đã được bỏ khỏi Gateway. Dùng `chan-intel-sync` hoặc
`chan-intel-import` của `codebase/intel`.
