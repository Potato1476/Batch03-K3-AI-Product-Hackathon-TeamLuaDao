# Backend CHẮN — service `/v1` công khai (Gateway + Detection + Lookup)

## Context

Repo hiện có hai nửa đã hoạt động và một nửa hoàn toàn còn trống:

- **Có rồi:** `repo/codebase/ml` (`chan_ml`) — model 8 dấu hiệu TF-IDF + LogisticRegression, policy L4 deterministic, recall 0.93 / FPR 0.026, 13 test xanh. Và `repo/codebase/api` (`chan_training_api`) — control plane nội bộ port 8001 cho continuous training (quarantine → review → retrain → promote), 7 test xanh.
- **Chưa có gì:** toàn bộ hợp đồng API người dùng ở §7 tài liệu kiến trúc. Grep cả repo cho `v1/analyze|v1/lookup|v1/rules|...` chỉ ra văn xuôi trong README. Không có endpoint `/v1` nào, không có 7 bảng ở §8, không có pgvector, không có Redis, không có L2 redactor (chỉ có *validator*), không có Rule Bundle.

Nghĩa là: model biết chấm điểm nhưng **không có đường nào để client gọi tới nó**. Đây là mảnh còn thiếu để Luồng A (người dùng chủ động hỏi) và Luồng C (chặn tại điểm chuyển tiền) chạy được đầu-cuối, và cũng là điều kiện để làm PWA/Android ở bước sau.

Mục tiêu: dựng service `/v1` công khai bám sát `repo/docs/CHAN-ARCHITECTURE.md` (nguồn sự thật duy nhất), tái sử dụng `chan_ml` làm tầng L3 thay vì viết lại logic chấm điểm, và thực thi 6 bất biến I1–I6 ở **tầng dữ liệu + test**, không chỉ ở tài liệu.

### Phạm vi đã chốt với người dùng

| Hạng mục | Chốt |
|---|---|
| L3 | `chan_ml` local là provider mặc định; thêm adapter LLM bật bằng env (`CHAN_L3_PROVIDER=local\|llm\|ensemble`) |
| Endpoint | Luồng A + C (Giai đoạn 1 §13): `analyze`, `ocr`, `lookup/{account,phone,url}`, `report`, `rules/bundle`, `feedback`. **Guardian: tạo bảng nhưng chưa làm endpoint** |
| OCR | `OcrEngine` protocol; provider `stub` mặc định (501), `paddle` lazy qua extra `[ocr]` |
| Vị trí code | Package mới `repo/codebase/gateway` (`chan_api`, port 8000). Không sửa `chan_training_api` |

### Giả định tôi tự quyết (nêu rõ để bạn phản đối được)

1. **Thêm `POST /v1/devices/token`** — không có trong §7, nhưng §7.3 yêu cầu "device token có thời hạn, xoay vòng định kỳ" và §8 có bảng `devices`. Không có endpoint cấp token thì không client nào gọi được 8 endpoint kia. Đây là hạ tầng auth, không phải tính năng mới.
2. **`engine_version` trả về chuỗi `ml-*`** của model đang active (ví dụ `ml-20260730-101500-a1b2c3d4`), không phải `de-1.4.0` như ví dụ §7. Ví dụ trong tài liệu là giá trị cũ, không khớp `ENGINE_VERSION` trong code. Tôi sẽ ghi một dòng đính chính vào `docs/CHAN-ARCHITECTURE.md`.
3. **Không scrape tinnhiemmang.vn / checkscam.vn.** Cung cấp CLI import từ file để nạp blocklist; việc lấy dữ liệu từ nguồn ngoài là vấn đề pháp lý/thoả thuận, không phải kỹ thuật (§13 GĐ4 cũng xếp nó ngoài phạm vi).

---

## Kiến trúc thư mục

```
repo/codebase/
├─ ml/                       # sửa nhẹ: + redact.py, + kwarg blocklist_match
├─ api/                      # KHÔNG SỬA (trừ privacy.py delegate)
├─ rules/                    # ★ MỚI — Rule Bundle: nguồn duy nhất cho L0+L1
│  ├─ bundle.json            #   version, otp_patterns, l1_rules, gate, watchlist
│  └─ hotlines.json          #   verified_hotline theo cơ quan
├─ gateway/                  # ★ MỚI — chan-gateway, port 8000
│  ├─ src/chan_api/
│  │  ├─ main.py             #   create_app(), middleware, exception handlers
│  │  ├─ config.py           #   AppConfig.from_environment() — theo mẫu api/config.py
│  │  ├─ deps.py             #   DI: repo, redis, model registry, classifier
│  │  ├─ auth.py             #   device token: cấp, xác thực, xoay vòng
│  │  ├─ ratelimit.py        #   Redis fixed-window theo token + IP, fallback in-process
│  │  ├─ logging_safe.py     #   allowlist field + filter chặn nội dung lọt vào log
│  │  ├─ schemas.py          #   Pydantic v2, extra="forbid" (theo mẫu api/schemas.py)
│  │  ├─ repository.py       #   psycopg3 + pool, role read-mostly
│  │  ├─ model_registry.py   #   đọc model_versions, verify sha256, hot-swap
│  │  ├─ rules.py            #   load + ETag + cache Rule Bundle
│  │  ├─ hotlines.py         #   map dấu hiệu/keyword → verified_hotline
│  │  ├─ l3/{base,local,llm,similarity}.py
│  │  ├─ ocr/{base,stub,paddle}.py
│  │  ├─ routers/{analyze,ocr,lookup,report,rules,feedback,devices}.py
│  │  ├─ retention.py        #   CLI: TTL 90d analyses / 30d access log
│  │  └─ ingest.py           #   CLI: nạp blocklist từ file
│  ├─ migrations/002_public_v1.sql
│  └─ tests/
└─ docker-compose.yml        # ★ MỚI — pgvector + redis + gateway + training-api
```

---

## Thay đổi trong code đã có (giữ tối thiểu)

### 1. `ml/src/chan_ml/redact.py` — MỚI, L2 thật sự

Hiện `api/src/chan_training_api/privacy.py` chỉ **kiểm tra** text đã redact, không có ai *thực hiện* redact. `/v1/analyze` không thể chạy mà không có nó. Đặt trong `chan_ml` vì đây là hằng số dùng chung của hai service (tiền lệ: `normalize.py` đã ở đó và `chan_training_api` đang import).

```python
@dataclass(frozen=True)
class RedactionResult:
    text: str                      # đã thay placeholder, chỉ tồn tại trong RAM
    account_hashes: tuple[str,...] # SHA256 số TK — giữ riêng cho Lookup (§4)
    phone_hashes:   tuple[str,...]
    url_hashes:     tuple[str,...]
    otp_found: bool                # I1 — lớp phòng thủ thứ 2 sau L1

def redact_l2(text: str) -> RedactionResult
def verify_redacted(text: str) -> str   # regex chuyển từ privacy.py sang
```

Thứ tự thay thế quan trọng (OTP trước số TK trước SĐT trước số tiền), giữ đúng 5 placeholder §4: `<OTP> <ACCOUNT> <PHONE> <NAME> <AMOUNT:trieu>`. `<AMOUNT:trieu>` giữ bậc độ lớn (`trieu`/`ty`), bỏ giá trị chính xác.

`privacy.py` thành wrapper mỏng: `validate_l2_redacted = verify_redacted`, giữ `RedactionError` để 7 test hiện có của training API vẫn xanh (đặc biệt `test_redaction_failure_does_not_echo_raw_content`).

### 2. `ml/src/chan_ml/model.py` — thêm 1 kwarg

`aggregate_risk()` đã nhận `blocklist_match` ([policy.py:28](repo/codebase/ml/src/chan_ml/policy.py#L28)) nhưng `PhishingSignalModel.predict()` không thread nó xuống. Ghi đè cứng "số TK có trong blocklist → high" (§6) vì thế không tới được model. Thêm `blocklist_match: bool = False` vào `predict()` và truyền vào `aggregate_risk`. Backward-compatible, không test nào phải sửa.

### 3. `docs/CHAN-ARCHITECTURE.md` — đính chính `engine_version` (xem giả định #2).

---

## Migration `002_public_v1.sql`

Chép nguyên §8 tài liệu, thêm những thứ §8 bỏ trống:

- `CREATE EXTENSION IF NOT EXISTS vector;`
- 8 bảng: `analyses`, `scenarios`, `blocklist_accounts/phones/urls`, `devices`, `guardians`, `guardian_alerts`, `feedback` — kể cả 2 bảng guardian (endpoint để GĐ3, nhưng ràng buộc `consent_source = 'protected_device'` phải có sẵn ở tầng dữ liệu, đó là cách thực thi I5).
- `analyses`: **không có cột text** (I2). `signals jsonb` chỉ `[{code, confidence}]` — gateway phải strip `evidence` trước khi insert.
- `blocklist_*`: `prefix char(5)` + index, `CHECK (origin IN ('tinnhiemmang','checkscam','user_report','ncsc'))`.
- `scenarios.embedding vector(1024)` + `ivfflat` index, `CHECK` chỉ cho insert khi `consented = true` (§7.2).
- `access_log` (device_id hash, endpoint, status, latency_ms — **không có nội dung**), TTL 30 ngày.
- `devices.token_hash bytea` + `expires_at`, `rotated_from text`.

Chạy bằng `psql chan < ...` giống 001 (repo chưa có migration runner, đừng thêm alembic cho một file).

---

## Các endpoint

### `POST /v1/analyze` — tim của hệ thống

Pipeline, mỗi bước là một hàm test được riêng:

1. **Auth + rate limit** — device token; giới hạn theo token *và* IP (§7.3 chống dùng làm LLM proxy miễn phí).
2. **Schema validate** — `AnalyzeRequest` khớp §7 chính xác: `text, source, input_mode, app_package, local_signals, truncated, locale`. `extra="forbid"`, `text` max 4000.
   `local_signals` là **từ vựng riêng của L1**, không phải 8 signal code (`aggregate_risk` sẽ raise `ValueError` nếu nhét vào). Định nghĩa enum trong Rule Bundle (`url_shortened`, `apk_link`, `otp_pattern`, `blocklist_hit`) và chỉ dùng để cộng thêm confidence cho signal tương ứng, có trần.
3. **L2 redact** — `redact_l2(text)`. Nếu `otp_found` → trả `risk: high` ngay với signal `yeu_cau_otp` (I1), không gọi model, không lookup.
4. **Lookup blocklist** — hash TK/SĐT/URL từ bước 3 đối chiếu blocklist server-side (đây là hash server tự tính từ text, khác `/v1/lookup/*` nơi client chủ động tra — I4 chỉ áp cho endpoint lookup).
5. **L3** — `SignalClassifier.classify(redacted_text)` + `similarity_max` từ pgvector song song (`asyncio.gather`).
6. **L4** — `aggregate_risk(signals, similarity_max=, similarity_beta=, blocklist_match=)`. **Không viết lại công thức**, gọi thẳng `chan_ml.policy`.
7. **Định hình output** — `analysis_id` (`an_` + 12 hex), `explanation`/`questions` từ `chan_ml`, `verified_hotline` từ `hotlines.json`, `actions`, `engine_version`, `rule_bundle_version`.
8. **Persist** — insert `analyses` với signals **đã strip evidence**. Text và explanation không bao giờ ra khỏi RAM.

Chạy inference trong `run_in_threadpool` — model là sklearn sync, p95 phải < 5s (§11.4) và event loop không được block.

### `GET /v1/lookup/{account,phone,url}`

Chỉ nhận `?prefix=` — **5 ký tự hex, regex `^[0-9a-f]{5}$`**. Nhận giá trị thô là vi phạm I4, nên schema phải từ chối ở tầng validate, không phải bằng quy ước. Trả về cả cụm hash cùng prefix (`{prefix, hashes: [{hash, report_cnt, last_seen}], bundle_version}`), client tự đối chiếu. Cache Redis theo prefix. Không log prefix vào access_log (log prefix nhiều lần vẫn thu hẹp được không gian tra cứu).

### `POST /v1/report`

Nhận `{kind: account|phone|url, value_sha256, evidence_analysis_id?}` — client hash trước, server không nhận giá trị thô. Upsert `blocklist_*` với `origin='user_report'`, `report_cnt = report_cnt + 1`. Chống spam: rate limit theo device + trần số report/ngày.

### `GET /v1/rules/bundle`

Trả `codebase/rules/bundle.json` nguyên văn + `ETag` (sha256 của nội dung) + `Cache-Control`. Hỗ trợ `If-None-Match` → 304. Đây là thứ bảo đảm tương đương Web ↔ Android **bằng dữ liệu** (§3): bản TS và bản Kotlin đọc cùng một file, nên không thể lệch L1.

### `POST /v1/feedback`

Chỉ ghi `{analysis_id, verdict}` vào bảng `feedback` (§8). Nếu người dùng **bấm đồng ý góp dữ liệu riêng** (`contribute: true` + `redacted_text`), gateway gọi `POST /internal/v1/training/scenarios` của training API với `rights_basis="explicit_consent", consented=true`. Đây là chiếc cầu duy nhất từ public sang private plane; mọi nhánh khác chỉ lưu verdict metadata (đúng `api/README.md:53-55`).

### `POST /v1/ocr` và `POST /v1/devices/token`

OCR: `OcrEngine` protocol, `stub` trả 501 `ocr_provider_not_configured`, `paddle` import lazy. Trả text về client để client tự gọi `/analyze` (§7) — server không tự chain, giữ ảnh chỉ trong RAM.

Devices: cấp token ngẫu nhiên 32 byte, lưu `sha256` + `expires_at`, trả plaintext đúng một lần. Endpoint xoay vòng ghi `rotated_from`.

---

## L3 — provider architecture

```python
# l3/base.py
@dataclass(frozen=True)
class SignalScore:
    code: str; confidence: float; evidence: str

class SignalClassifier(Protocol):
    async def classify(self, redacted_text: str) -> list[SignalScore]: ...
```

- **`local.py`** (mặc định) — `LocalModelClassifier` đọc model qua `model_registry`, gọi `chan_ml` trong threadpool. Offline, chi phí 0, p50 ~2.3ms.
- **`llm.py`** — Claude structured JSON. §0 bắt buộc: nội dung tin nhắn là **dữ liệu không tin cậy**, phải bọc trong thẻ phân định (`<untrusted_message>`), không nối vào system prompt. Bắt buộc trả `evidence` là đoạn trích thật (§5). Timeout + circuit breaker, không log prompt/response.
- **`similarity.py`** — embedding text đã ẩn danh → pgvector cosine trên `scenarios` (chỉ hàng `consented=true`) → `similarity_max`. `similarity_beta` mặc định 0.0 khi kho rỗng, 0.15 khi đã có dữ liệu (theo `ml/README.md`).
- **`ensemble`** — max-pool confidence theo từng code giữa local và llm. Ưu tiên recall trên precision (§11).

`model_registry.py` đọc **read-only** bảng `model_versions`, verify sha256, `joblib.load`, `isinstance` check, hot-swap dưới `RLock` — cùng thuật toán `chan_training_api/active_model.py:29-46`. Tôi **không** import package private vào process public: gateway phải chạy bằng DB role read-only và không được nạp `chan_training_api` (nơi có repository ghi được vào quarantine/training_runs). Đánh đổi có ý thức: ~45 dòng trùng lặp để đổi lấy ranh giới private/public rạch ròi. Sẽ ghi comment trỏ chéo hai file.

---

## Thực thi bất biến bằng test, không bằng tài liệu

Đây là phần tôi coi là quan trọng nhất — mỗi bất biến I1–I6 có một test tự động sẽ đỏ nếu ai đó phá:

| # | Test |
|---|---|
| I1 | text chứa OTP → `risk=high`, **không** có request nào tới classifier; `redact_l2` output không còn chữ số OTP |
| I2 | sau `POST /v1/analyze`, dump toàn bộ hàng `analyses` → không hàng nào chứa substring của text gốc; `signals` không có key `evidence` |
| I3 | test tài liệu hoá cửa lọc L1: golden set qua Rule Bundle → tỷ lệ vượt ngưỡng ≤ ~5%, và metric này expose ở `/metrics` |
| I4 | `GET /v1/lookup/account?value=123` → 422; `?prefix=abcdef` (6 ký tự) → 422; chỉ `^[0-9a-f]{5}$` qua |
| I5 | insert `guardians` với `consent_source != 'protected_device'` → DB raise |
| I6 | fuzz mọi input qua `/v1/analyze`, assert `risk ∈ {high, medium, unknown}`; grep source tree không có literal `"safe"`/`"ok"`/`"clean"` trong enum risk. (`chan_ml` đã có `test_unknown_signal_is_rejected` làm tiền lệ) |
| Log | `caplog` bao quanh một lần analyze đầy đủ → không record nào chứa text/explanation/evidence/prefix |
| Parity | cùng một text với `source=web\|android\|zalo_oa` → `risk` + `signals` trùng khớp (§11.3) |

Theo mẫu test đã có: `FakeRepository` dict-backed + `app.dependency_overrides`, không cần Postgres thật cho phần lớn test (giống `api/tests/test_api.py`). Riêng nhóm test ràng buộc DB (I5, unique index, CHECK) chạy có mark `@pytest.mark.postgres`, skip khi không có `CHAN_TEST_DATABASE_URL`.

---

## Thứ tự thực hiện

1. `chan_ml/redact.py` + `privacy.py` delegate + kwarg `blocklist_match` → chạy 20 test hiện có, phải xanh hết.
2. `codebase/rules/bundle.json` + `hotlines.json` (nguồn duy nhất cho L0+L1).
3. Scaffold `codebase/gateway`: pyproject, config, main, deps, logging_safe, healthz.
4. `002_public_v1.sql` + `repository.py` + `docker-compose.yml` (pgvector/pgvector:pg16 + redis).
5. auth + ratelimit + `POST /v1/devices/token`.
6. `model_registry` + `l3/local` + `/v1/analyze` (đường xương sống) + test bất biến I1/I2/I6.
7. `/v1/lookup/*` + `/v1/report` + `ingest.py` CLI + test I4.
8. `/v1/rules/bundle` + `/v1/feedback` (+ cầu sang training API).
9. `/v1/ocr` stub + protocol, `l3/llm.py`, `l3/similarity.py`.
10. `retention.py` CLI, `/metrics`, README gateway, đính chính doc.

---

## Verification

**Chạy được đầu-cuối:**

```bash
cd repo
docker compose up -d postgres redis
psql "$CHAN_DATABASE_URL" < codebase/api/migrations/001_continuous_training.sql
psql "$CHAN_DATABASE_URL" < codebase/gateway/migrations/002_public_v1.sql

.venv/bin/python -m pip install -e 'codebase/ml[dev]' -e 'codebase/gateway[dev]'
.venv/bin/chan-generate --size 100000 --output .local/data/chan-synthetic.jsonl.gz
.venv/bin/chan-train --dataset .local/data/chan-synthetic.jsonl.gz   # sinh model active
.venv/bin/chan-gateway                                               # port 8000
```

**Test tự động:**

```bash
.venv/bin/pytest -q codebase/ml/tests codebase/api/tests codebase/gateway/tests
CHAN_TEST_DATABASE_URL=... .venv/bin/pytest -q -m postgres codebase/gateway/tests
```
Điều kiện đạt: 20 test cũ vẫn xanh + toàn bộ test bất biến xanh.

**Kiểm tra bằng tay 3 luồng:**

```bash
TOKEN=$(curl -sX POST localhost:8000/v1/devices/token -d '{"platform":"web"}' | jq -r .token)

# Luồng A — tin lừa đảo → high, có explanation + questions + hotline
curl -sX POST localhost:8000/v1/analyze -H "Authorization: Bearer $TOKEN" \
  -d '{"text":"Toi la can bo thue, anh chuyen 20 trieu vao 0123456789 truoc 17h hom nay, khong noi voi ai","source":"web","input_mode":"manual","truncated":false,"locale":"vi-VN"}' | jq

# I1 — có OTP → high, và không byte nào của mã tới model
curl -sX POST localhost:8000/v1/analyze -H "Authorization: Bearer $TOKEN" \
  -d '{"text":"Doc ma 938271 de xac minh","source":"web","input_mode":"manual","truncated":false,"locale":"vi-VN"}' | jq .risk

# I6 — tin hợp pháp phải là "unknown", KHÔNG BAO GIỜ "an toàn"
curl -sX POST localhost:8000/v1/analyze -H "Authorization: Bearer $TOKEN" \
  -d '{"text":"Nha truong thong bao hop phu huynh sang thu 7","source":"web","input_mode":"manual","truncated":false,"locale":"vi-VN"}' | jq '.risk, .explanation'

# Luồng C — k-anonymity
curl -s "localhost:8000/v1/lookup/account?prefix=a1b2c" -H "Authorization: Bearer $TOKEN" | jq
curl -s "localhost:8000/v1/lookup/account?value=0123456789" -H "Authorization: Bearer $TOKEN"  # phải 422
```

**Ngưỡng chấp nhận (§11.4)** — chạy golden set qua `/v1/analyze` thật, không chỉ qua model:
recall ≥ 90% nhóm lừa đảo · FP < 15% nhóm hợp pháp · p95 < 5s. Ghi kết quả vào `repo/eval/results.md`.

**I2 kiểm chứng bằng mắt:** sau khi analyze, `psql -c 'select * from analyses'` — không thấy chữ nào của tin nhắn.
