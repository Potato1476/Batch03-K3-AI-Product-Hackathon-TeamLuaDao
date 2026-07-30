# CHẮN Gateway — Hướng dẫn cài đặt và chạy

Service `/v1` công khai: API Gateway + Detection Engine (L2–L4) + Lookup Service.
Chạy ở **port 8000**. Tách biệt với training control plane nội bộ ở port 8001
(`codebase/api`) — xem [Ranh giới hai service](#ranh-giới-hai-service).

> Mọi lệnh trong tài liệu này đã được chạy và kiểm chứng thực tế trên macOS
> (Darwin 25.5.0) với Python 3.11 và Docker. Kết quả thật được ghi ở mục
> [Kiểm chứng](#kiểm-chứng).

---

## 0. Yêu cầu

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | **≥3.11, <3.14** | `chan_ml` không hỗ trợ 3.14. Nếu máy bạn mặc định 3.14, xem [Lỗi thường gặp](#lỗi-thường-gặp) |
| PostgreSQL | 16 + **pgvector** | dùng image `pgvector/pgvector:pg16` là gọn nhất |
| Redis | 7 | tuỳ chọn — không có thì rate limit chạy trong tiến trình |
| Docker | có compose v2 | chỉ cần nếu dùng cách A |

Kiểm tra Python:

```bash
python3.11 --version    # cần thấy 3.11.x
```

---

## 1. Cách nhanh nhất — Docker Compose (toàn bộ hạ tầng)

Chạy **từ thư mục `repo/codebase`**:

```bash
cd repo/codebase
docker compose up -d postgres redis
```

Compose tự động áp dụng cả hai migration khi volume còn trống
(`001_continuous_training.sql` rồi `002_public_v1.sql`). Chờ tới khi healthy:

```bash
docker compose ps          # cả hai phải là "Up (healthy)"
docker compose exec postgres psql -U chan -d chan -c "\dt"
```

Phải thấy 16 bảng (9 bảng public + 4 bảng training + phụ trợ).

Sau đó build và chạy gateway trong container:

```bash
docker compose up --build gateway
```

Hoặc — **khuyến nghị khi phát triển** — chỉ dùng compose cho postgres/redis rồi
chạy gateway từ source (mục 2), vì như vậy sửa code là thấy ngay.

---

## 2. Chạy từ source (khuyến nghị khi phát triển)

### 2.1. Tạo môi trường ảo và cài package

Chạy **từ thư mục `repo`**:

```bash
cd repo
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip

# Thứ tự quan trọng: chan-ml là package local, phải cài trước.
.venv/bin/python -m pip install -e 'codebase/ml[dev]'
.venv/bin/python -m pip install -e 'codebase/gateway[dev]'

# Tuỳ chọn: training control plane (chỉ cần nếu muốn thử /v1/feedback contribute)
.venv/bin/python -m pip install -e 'codebase/api[dev]'
```

Kiểm tra:

```bash
.venv/bin/python -c "import chan_ml, chan_api; print('ok')"
```

### 2.2. Chuẩn bị cơ sở dữ liệu

Nếu đã dùng compose ở mục 1 thì **bỏ qua bước này** — migration đã chạy rồi.

Nếu dùng PostgreSQL cài sẵn trên máy:

```bash
createdb chan
psql chan -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql chan < codebase/api/migrations/001_continuous_training.sql
psql chan < codebase/gateway/migrations/002_public_v1.sql
```

> `002` cần bảng `training_runs` và `model_versions` do `001` tạo ra (gateway đọc
> `model_versions` để biết model nào đang active), nên phải chạy `001` trước.

### 2.3. Cấu hình biến môi trường

```bash
cp codebase/gateway/.env.example codebase/gateway/.env
```

Tối thiểu chỉ cần một biến:

```bash
export CHAN_DATABASE_URL='postgresql://chan:chan@localhost:5432/chan'
```

`CHAN_RULES_DIR` **không cần đặt** khi chạy từ source: service tự tìm
`codebase/rules`. Danh sách đầy đủ các biến nằm trong
[`.env.example`](.env.example).

### 2.4. Nạp một model active (BẮT BUỘC)

`/v1/analyze` trả **503 `detection_engine_unavailable`** nếu chưa có model nào
active — gateway chỉ đọc model từ bảng `model_versions`, nó không tự train.

Cách nhanh cho môi trường local:

```bash
CHAN_DATABASE_URL='postgresql://chan:chan@localhost:5432/chan' \
CHAN_MODEL_ARTIFACT_ROOT="$PWD/.local/model-registry" \
.venv/bin/python codebase/gateway/scripts/seed_local_model.py --size 30000
```

Kết quả thật khi chạy lệnh trên:

```
generating 30000 synthetic records...
training on 23949 records...
evaluating on 3004 records...
  recall=0.9376 fpr=0.0270 risk_accuracy=0.8745

active model: ml-local-20260730-051718
artifact:     .../repo/.local/model-registry/ml-local-20260730-051718.joblib
```

Mất khoảng 1–2 phút. Dùng `--size 100000` để đạt chất lượng như bản baseline
trong `repo/eval/`.

> ⚠️ Script này **bỏ qua toàn bộ cổng kiểm tra promotion** (recall ≥ 90%,
> FP < 15%, không hồi quy). Nó chỉ dành cho máy phát triển. Trên production,
> hàng active phải do training worker ghi sau khi qua gate — xem
> [`../api/README.md`](../api/README.md).

### 2.5. Chạy server

```bash
CHAN_DATABASE_URL='postgresql://chan:chan@localhost:5432/chan' \
CHAN_REDIS_URL='redis://localhost:6379/0' \
.venv/bin/chan-gateway
```

Server lắng nghe `http://0.0.0.0:8000`. Log ra stdout dạng JSON có cấu trúc.

Cách khác, tương đương:

```bash
.venv/bin/uvicorn chan_api.main:app --host 0.0.0.0 --port 8000 --access-log=false
```

> `--access-log=false` là **có chủ ý**: access log của uvicorn in cả query
> string, trong đó có prefix tra cứu — ghi lại nhiều lần sẽ thu hẹp không gian
> tra cứu và làm xói mòn bất biến I4. Logger của service đã ghi request rồi,
> nhưng chỉ ghi path.

Chế độ tự reload khi sửa code:

```bash
CHAN_DATABASE_URL='...' .venv/bin/uvicorn chan_api.main:app --reload --port 8000
```

### 2.6. Kiểm tra server sống

```bash
curl -s localhost:8000/healthz    # {"status":"ok"}
curl -s localhost:8000/readyz     # {"status":"ready","model_version":"ml-local-..."}
```

`/healthz` chỉ nói tiến trình còn sống. **`/readyz` mới là cái cần theo dõi**:
nó trả 503 khi chưa nạp được model, tức là `/v1/analyze` chưa dùng được. Dùng
`/readyz` cho readiness probe, `/healthz` cho liveness probe.

Xem API docs tự sinh: <http://localhost:8000/docs>

---

## 3. Thử toàn bộ luồng nghiệp vụ

### 3.1. Lấy device token

Không cần tài khoản, không cần số điện thoại (§7.3).

```bash
TOKEN=$(curl -s -X POST localhost:8000/v1/devices/token \
  -H 'Content-Type: application/json' -d '{"platform":"web"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
H="Authorization: Bearer $TOKEN"
```

Token chỉ trả về **một lần**; server chỉ lưu SHA-256 của nó.

### 3.2. Luồng A — người dùng chủ động hỏi

```bash
curl -s -X POST localhost:8000/v1/analyze -H "$H" -H 'Content-Type: application/json' -d '{
  "text":"Toi la can bo thue, anh Nguyen Van Hung chuyen 20 trieu vao 19001234567890 truoc 17h hom nay, khong noi voi ai ke ca gia dinh",
  "source":"web","input_mode":"manual","truncated":false,"locale":"vi-VN"}' | python3 -m json.tool
```

Kết quả thật (đã lược `evidence` cho gọn):

```json
{
  "analysis_id": "an_cbb26cc0d1bd",
  "risk": "medium",
  "score": 0.691981,
  "signals": [
    {"code": "yeu_cau_bi_mat",      "confidence": 1.0},
    {"code": "tk_ca_nhan",          "confidence": 1.0},
    {"code": "mao_danh_tham_quyen", "confidence": 0.9598},
    {"code": "ap_luc_thoi_gian",    "confidence": 0.9999}
  ],
  "explanation": "Người gửi yêu cầu giữ bí mật với gia đình. Tin nhắn yêu cầu chuyển tiền vào tài khoản cá nhân. Tin nhắn tự nhận là cơ quan hoặc tổ chức có thẩm quyền.",
  "questions": ["Tại sao việc này lại không được nói với người thân?",
                "Tại sao tiền lại chuyển vào tài khoản cá nhân?"],
  "verified_hotline": {"name": "Tổng cục Thuế", "number": "19008888"},
  "actions": ["report", "share_to_guardian", "lookup_account"],
  "engine_version": "ml-local-20260730-051718",
  "rule_bundle_version": "rb-2026-07-30"
}
```

### 3.3. Bất biến I1 — có OTP thì dừng tại chỗ

```bash
curl -s -X POST localhost:8000/v1/analyze -H "$H" -H 'Content-Type: application/json' \
 -d '{"text":"Doc ma 938271 de xac minh tai khoan","source":"web","input_mode":"manual","truncated":false,"locale":"vi-VN"}'
```

→ `risk: high`, `score: 0.0`, dấu hiệu duy nhất `yeu_cau_otp`, và **model không
hề được gọi**. Sáu chữ số đó không xuất hiện trong response, trong log, hay
trong database.

### 3.4. Bất biến I6 — tin hợp pháp là "unknown", không bao giờ "an toàn"

```bash
curl -s -X POST localhost:8000/v1/analyze -H "$H" -H 'Content-Type: application/json' \
 -d '{"text":"Nha truong thong bao hop phu huynh lop 5A sang thu 7 tuan nay","source":"web","input_mode":"manual","truncated":false,"locale":"vi-VN"}'
```

→ `risk: unknown`, `explanation: "Chưa phát hiện dấu hiệu."`, `signals: []`.

### 3.5. Luồng C — chặn tại điểm chuyển tiền (k-anonymity)

Client hash số tài khoản rồi **chỉ gửi 5 ký tự hex đầu**:

```bash
# Bước 1: client tự hash (đây là việc của client, làm ở đây để minh hoạ)
eval $(.venv/bin/python -c "
from chan_ml.redact import hash_identifier, hash_prefix
h = hash_identifier('19001234567890')
print(f'HASH={h}'); print(f'PREFIX={hash_prefix(h)}')")

# Bước 2: báo cáo (gửi hash, KHÔNG gửi số)
curl -s -X POST localhost:8000/v1/report -H "$H" -H 'Content-Type: application/json' \
 -d "{\"kind\":\"account\",\"value_sha256\":\"$HASH\"}"
# → {"kind":"account","report_cnt":1,"accepted":true}

# Bước 3: tra cứu theo prefix — server trả cả cụm hash
curl -s "localhost:8000/v1/lookup/account?prefix=$PREFIX" -H "$H" | python3 -m json.tool

# Bước 4: client tự đối chiếu hash của mình trong cụm, tại chỗ
```

Server không bao giờ biết bạn tra số nào. Thử gửi giá trị thô sẽ bị từ chối:

```bash
curl -s -o /dev/null -w '%{http_code}\n' "localhost:8000/v1/lookup/account?value=19001234567890" -H "$H"
# → 422
curl -s -o /dev/null -w '%{http_code}\n' "localhost:8000/v1/lookup/account?prefix=abcdef" -H "$H"
# → 422 (6 ký tự cũng không được, chỉ đúng 5 hex)
```

Sau khi số TK đã bị báo cáo, ghi đè cứng §6 có hiệu lực:

```bash
curl -s -X POST localhost:8000/v1/analyze -H "$H" -H 'Content-Type: application/json' \
 -d '{"text":"Ban chuyen tien vao 19001234567890 giup minh nhe","source":"web","input_mode":"manual","truncated":false,"locale":"vi-VN"}'
```

→ `risk: high` dù `score` chỉ 0.31, kèm giải thích "Số tài khoản trong tin nhắn
này đã bị người khác báo cáo là lừa đảo. Đừng chuyển tiền."

### 3.6. Rule Bundle

```bash
curl -s -D - localhost:8000/v1/rules/bundle -o /tmp/bundle.json | grep -i 'etag\|x-chan'
# etag: "dd3acf884a6022e9ca4042adb503c59a"
# x-chan-bundle-version: rb-2026-07-30

# Trả về nguyên văn byte-for-byte codebase/rules/bundle.json
diff <(cat codebase/rules/bundle.json) /tmp/bundle.json && echo "khớp tuyệt đối"

# Hỗ trợ điều kiện — client offline không cần tải lại
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/v1/rules/bundle \
  -H 'If-None-Match: "dd3acf884a6022e9ca4042adb503c59a"'   # → 304
```

Endpoint này **không cần token**: client cần L0+L1 trước khi có token, và cần
chạy được cả khi offline.

### 3.7. Feedback

```bash
AID=<analysis_id lấy từ bước 3.2>
curl -s -X POST localhost:8000/v1/feedback -H "$H" -H 'Content-Type: application/json' \
 -d "{\"analysis_id\":\"$AID\",\"verdict\":\"correct\"}"
# → {"recorded":true,"contributed":false}
```

Mặc định chỉ lưu verdict. Chỉ khi người dùng **bấm đồng ý góp dữ liệu** thì text
đã ẩn danh mới được chuyển sang training plane (cần `CHAN_TRAINING_API_URL` +
`CHAN_TRAINING_API_KEY`). Text chưa ẩn danh bị từ chối và **không** bị echo lại:

```bash
curl -s -X POST localhost:8000/v1/feedback -H "$H" -H 'Content-Type: application/json' \
 -d "{\"analysis_id\":\"$AID\",\"verdict\":\"false_negative\",\"contribute\":true,\"redacted_text\":\"Gui ma 938271 cho toi ngay\",\"signals\":[\"yeu_cau_otp\"]}"
# → {"detail":"content_failed_redaction_check"}   (không có "938271" trong response)
```

### 3.8. OCR

Mặc định provider là `stub`, trả lỗi rõ ràng thay vì text rỗng:

```bash
curl -s -X POST localhost:8000/v1/ocr -H "$H" -F "image=@shot.png;type=image/png"
# → {"detail":"ocr_provider_not_configured"}
```

Bật PaddleOCR thật (nặng ~500MB):

```bash
.venv/bin/python -m pip install -e 'codebase/gateway[ocr]'
export CHAN_OCR_PROVIDER=paddle
```

---

## 4. Bật tầng LLM cho L3 (tuỳ chọn)

Mặc định L3 dùng model `chan_ml` local: offline, chi phí 0, p50 ~2ms. Muốn dùng
LLM theo §5/§12:

```bash
.venv/bin/python -m pip install -e 'codebase/gateway[llm]'
export ANTHROPIC_API_KEY='sk-ant-...'
export CHAN_L3_PROVIDER=llm        # hoặc: ensemble
```

| Giá trị | Hành vi |
|---|---|
| `local` | chỉ `chan_ml` (mặc định) |
| `llm` | gọi Claude; **tự động fallback về local** khi lỗi/timeout |
| `ensemble` | chạy cả hai, max-pool theo từng dấu hiệu (ưu tiên recall theo §11) |

Hai điều được thực thi trong code, không phải quy ước:
nội dung tin nhắn đi vào prompt trong thẻ `<untrusted_message>` và system prompt
nói rõ đó là dữ liệu cần phân loại chứ không phải chỉ thị (§0); và `evidence` do
LLM trả về bị **đối chiếu ngược với văn bản** — trích dẫn bịa sẽ bị xoá và hạ
điểm dấu hiệu đó xuống dưới ngưỡng.

---

## 5. Chạy test

```bash
cd repo
.venv/bin/pytest -q codebase/ml/tests codebase/api/tests codebase/gateway/tests
```

Toàn bộ suite chạy **offline** — không cần Postgres, không cần Redis, không cần
API key. Postgres được thay bằng fake trong bộ nhớ, model là một bản fit sklearn
thật nhưng nhỏ.

Nhóm test cần DB thật (ràng buộc CHECK, unique index) chạy riêng:

```bash
export CHAN_TEST_DATABASE_URL='postgresql://chan:chan@localhost:5432/chan'
.venv/bin/pytest -q -m postgres codebase/gateway/tests
```

Đáng chú ý: mỗi bất biến I1–I6 có test riêng trong
[`tests/test_invariants.py`](tests/test_invariants.py), và
[`tests/test_no_content_in_logs.py`](tests/test_no_content_in_logs.py) chạy một
request đầy đủ rồi khẳng định không mảnh nội dung nào lọt vào log.

---

## 6. Công việc định kỳ

```bash
# Xoá dữ liệu hết hạn (§7.2: analyses 90 ngày, access_log 30 ngày). Chạy hằng ngày.
CHAN_DATABASE_URL='...' .venv/bin/chan-retention

# Nạp blocklist từ file được phép sử dụng
CHAN_DATABASE_URL='...' .venv/bin/chan-blocklist-import \
  --kind account --source checkscam --file accounts.txt --dry-run
```

`chan-blocklist-import` **không crawl** tinnhiemmang.vn/checkscam.vn: được lấy gì
từ các nguồn đó là câu hỏi thoả thuận, không phải câu hỏi kỹ thuật. Nó nhận file
(một giá trị mỗi dòng, hoặc CSV với `--column`), tự normalize + hash, và chỉ ghi
digest + prefix — giá trị thô không vào database.

---

## Ranh giới hai service

| | Gateway (service này) | Training API (`codebase/api`) |
|---|---|---|
| Port | **8000** — công khai | **8001** — nội bộ, không expose |
| Auth | device token, xoay vòng được | shared secret tĩnh giữa các service |
| Endpoint | `/v1/*` | `/internal/v1/training/*` |
| Quyền DB | nên dùng role read-mostly | ghi được vào quarantine + training run |
| Model | **chỉ đọc** `model_versions` | ghi hàng active sau khi qua gate |

Gateway **không import** `chan_training_api`. Đây là lựa chọn có ý thức: nó
đánh đổi ~45 dòng trùng lặp trong `model_registry.py` (thuật toán nạp artifact
giống `active_model.py`) để lấy bảo đảm rằng một gateway bị chiếm quyền cũng
không thể đầu độc dữ liệu huấn luyện. Khi sửa một trong hai loader, hãy sửa cả
hai.

---

## Lỗi thường gặp

**`detection_engine_unavailable` (503) khi gọi `/v1/analyze`**
Chưa có model active. Chạy bước [2.4](#24-nạp-một-model-active-bắt-buộc). Kiểm tra:

```bash
psql "$CHAN_DATABASE_URL" -c "SELECT version, status FROM model_versions;"
curl -s localhost:8000/readyz
```

**`rule_bundle_unavailable` (503)**
Không tìm thấy `bundle.json`. Khi chạy từ source, service tự tìm
`codebase/rules`; nếu bạn chạy từ nơi khác thì đặt `CHAN_RULES_DIR` trỏ tới thư
mục đó. Kiểm tra:

```bash
.venv/bin/python -c "from chan_api.config import AppConfig; c=AppConfig.from_environment(); print(c.bundle_path, c.bundle_path.exists())"
```

**`ERROR: type "vector" does not exist` khi chạy migration**
Chưa bật pgvector. Dùng image `pgvector/pgvector:pg16`, hoặc
`CREATE EXTENSION vector;` trên PostgreSQL có sẵn extension.

**`relation "model_versions" does not exist`**
Chạy `002` trước `001`. Chạy `001_continuous_training.sql` trước.

**`ERROR: Could not find a version that satisfies chan-ml`**
Cài `codebase/ml` trước `codebase/gateway`: `chan-ml` là package local, không có
trên PyPI, nên nó không được khai báo trong `dependencies`.

**Python 3.14 → `requires-python` không khớp**
`chan_ml` giới hạn `<3.14` (phụ thuộc scikit-learn). Tạo venv bằng 3.11:

```bash
python3.11 -m venv .venv    # KHÔNG dùng python3 nếu python3 là 3.14
```

**`Form data requires "python-multipart"`**
Cài lại gateway: `pip install -e 'codebase/gateway[dev]'`. Đây là dependency
bắt buộc của `/v1/ocr`.

**Rate limit chặn khi đang thử nghiệm**
Mặc định 20 lần `/v1/analyze` mỗi phút cho mỗi device. Nới ra khi dev:

```bash
export CHAN_ANALYZE_PER_DEVICE_PER_MINUTE=1000
export CHAN_ANALYZE_PER_IP_PER_MINUTE=1000
```

**Sửa code mà server không đổi hành vi**
Còn tiến trình cũ đang giữ port. `pkill -f chan-gateway` rồi chạy lại, hoặc dùng
`uvicorn --reload`.

---

## Kiểm chứng

Số liệu thật, đo trên máy phát triển (macOS, Python 3.11, Postgres 16 trong
Docker, model seed 30k bản ghi):

| Hạng mục | Kết quả | Ngưỡng §11.4 |
|---|---|---|
| Độ trễ `/v1/analyze` p50 | **8.2 ms** | — |
| Độ trễ `/v1/analyze` p95 | **28.1 ms** | < 5000 ms ✔ |
| Recall (validation, model seed) | **0.9376** | ≥ 0.90 ✔ |
| False positive rate | **0.0270** | < 0.15 ✔ |
| Test | **164 passed** | — |

Kiểm chứng I2 bằng mắt — sau khi phân tích 9 tin nhắn, đọc thẳng database:

```bash
docker compose exec postgres psql -U chan -d chan -x \
  -c "SELECT id, encode(text_sha256,'hex'), risk, score, signals FROM analyses LIMIT 1;"
```

Chỉ thấy hash, mã dấu hiệu và điểm — không một chữ nào của tin nhắn, và
`signals` không có khoá `evidence`.

Ba bất biến được database **chủ động từ chối** vi phạm, không chỉ dựa vào code:

```bash
# I2 — signals kèm evidence
INSERT INTO analyses (...) VALUES (..., '[{"code":"tk_ca_nhan","evidence":"..."}]');
# ERROR: violates check constraint "analyses_signals_have_no_evidence"

# I5 — guardian không có consent từ máy người được bảo vệ
INSERT INTO guardians (..., consent_source) VALUES (..., 'remote_admin');
# ERROR: violates check constraint "guardians_consent_source_check"

# I6 — nhãn "safe"
INSERT INTO analyses (..., risk, ...) VALUES (..., 'safe', ...);
# ERROR: violates check constraint "analyses_risk_check"
```

---

## Tham chiếu

- Kiến trúc (nguồn sự thật): [`../../docs/CHAN-ARCHITECTURE.md`](../../docs/CHAN-ARCHITECTURE.md)
- Training control plane: [`../api/README.md`](../api/README.md)
- Model card: [`../ml/MODEL_CARD.md`](../ml/MODEL_CARD.md)
- Rule Bundle: [`../rules/bundle.json`](../rules/bundle.json)
- Toàn bộ biến môi trường: [`.env.example`](.env.example)
