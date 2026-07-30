# Kết quả các lượt chạy

**Quality bar (chốt 23:59 N1, không sửa sau đó):**
> "Đạt khi **≥90% golden set qua (≥18/20)**, **và** đồng thời trên bộ test hợp lệ
> của nhóm: **recall nhóm lừa đảo ≥ 90%**, **false positive nhóm hợp lệ < 15%**,
> **và** không case nào được gắn nhãn trấn an (`safe`/`an toàn`)."

Bar này không đặt mới: ba ngưỡng recall/FP/nhãn-cấm đã nằm sẵn trong code từ
trước — `acceptance` trong `chan_ml/evaluate_product.py` và `forbidden_labels`
trong `codebase/rules/bundle.json`. Mục ≥90% golden set là mức nhóm chốt thêm cho
bộ 20 case. **Cần một thành viên xác nhận bar này trước 23:59 N1** — sau thời
điểm đó không được sửa.

## Tổng hợp các lượt

| Lượt | Thời điểm | Người chạy | Thay đổi so với lượt trước | Pass / Tổng | % | Đối chiếu bar |
|---|---|---|---|---|---|---|
| 1 | 2026-07-30 11:38 | TODO (tên) | baseline — model `chan-team-typo-robust-20260730.3`, rule bundle `rb-2026-07-30.4` | 20/20 | 100% | ☑ Đạt |
| 2 | 2026-07-30 13:57 | TODO (tên) | rule bundle `rb-2026-07-30.5`: thêm rule escalation `risk_surface`; sửa va chạm "gấp"/"gặp" trong `time_pressure`. Model giữ nguyên. | 20/20 | 100% | ☑ Đạt |

Raw log: [`team-robust-final-golden-results.json`](team-robust-final-golden-results.json) (lượt 1) ·
[`rules-rb-20260730-5-golden-results.json`](rules-rb-20260730-5-golden-results.json) (lượt 2)

---

## Lượt 2 — 2026-07-30 13:57 (lượt hiện hành)

Model `chan-signal-model.joblib` · engine `ml-0.5.0` · rule bundle `rb-2026-07-30.5`

| ID | Loại | Kết quả thực tế | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| G01 | thường | `high` 0.76 · `ap_luc_thoi_gian`, `mao_danh_tham_quyen` | PASS | |
| G02 | thường | `high` 0.70 · `mao_danh_tham_quyen` | PASS | |
| G03 | thường | `high` 0.99 · `ap_luc_thoi_gian`, `tk_ca_nhan`, `yeu_cau_bi_mat` | PASS | |
| G04 | thường | `high` 1.00 · `yeu_cau_otp` | PASS | Chặn tại L1, không byte nào rời máy |
| G05 | thường | `high` 0.70 · `mao_danh_tham_quyen` | PASS | |
| G06 | thường | `high` 0.70 · `ap_luc_thoi_gian`, `mao_danh_tham_quyen` | PASS | |
| G07 | thường | `high` 0.70 · `loi_ich_bat_thuong` | PASS | |
| G08 | thường | `high` 0.73 · `cai_app_ngoai`, `mao_danh_tham_quyen` | PASS | |
| G09 | ① | `unknown` 0.00 · `[]` | PASS | Không bịa dấu hiệu trên input rác |
| G10 | ① | `unknown` 0.00 · `[]` | PASS | |
| G11 | ② | `medium` 0.35 · `[]` | PASS | Đúng khoảng medium nhưng **không nêu được dấu hiệu nào** — người dùng nhận cảnh báo mà không có lý do |
| G12 | ② | `medium` 0.41 · `chuyen_kenh`, `loi_ich_bat_thuong` | PASS | |
| G13 | ③ | `unknown` 0.02 · `[]` | PASS | |
| G14 | ③ | `medium` 0.35 · `loi_ich_bat_thuong` | PASS | |
| G15 | ④ | `unknown` 0.02 · `[]` | PASS | SMS biến động số dư thật — không báo động nhầm |
| G16 | ④ | `unknown` 0.05 · `[]` | PASS | Đọc đúng ngữ cảnh cảnh báo của Công an |
| G17 | hiếm | `high` 0.70 · `mao_danh_tham_quyen` | PASS | Chuẩn hoá được chèn chấm |
| G18 | hiếm | `high` 0.70 · `ap_luc_thoi_gian`, `chuyen_kenh`, `loi_ich_bat_thuong` | PASS | |
| G19 | hiếm | `high` 0.70 · `ap_luc_thoi_gian` | PASS | Tách được `bit.ly` |
| G20 | hiếm | `high` 1.00 · `yeu_cau_otp` | PASS | Chặn tại L1 |

**Tỉ lệ pass theo lớp:** ① 100% (2/2) · ② 100% (2/2) · ③ 100% (2/2) · ④ 100% (2/2) · thường 100% (8/8) · hiếm 100% (4/4)

**Biến thể nhiễu chính tả:** 136/136 (100%) — 8 biến thể xác định mỗi case, seed `20260731`.

### Đo bổ sung trên bộ test lớn hơn của nhóm

`chan-evaluate-product` trên split `test` của `chan-team-clean-v4` (198 bản ghi:
125 lừa đảo, 73 hợp lệ) — raw log [`rules-rb-20260730-5-product-test.json`](rules-rb-20260730-5-product-test.json):

| Chỉ số | Giá trị | Bar | Đối chiếu |
|---|---|---|---|
| Recall nhóm lừa đảo | **0.936** | ≥ 0.90 | ☑ |
| False positive nhóm hợp lệ | **0.082** | < 0.15 | ☑ |
| Độ chính xác mức rủi ro | 0.828 | — | |
| Macro-F1 các dấu hiệu có mẫu | 0.866 | — | |

Ma trận nhầm lẫn: `high→high` 89 · `high→medium` 15 · **`high→unknown` 3** ·
`medium→high` 5 · `medium→medium` 8 · **`medium→unknown` 5** · `unknown→medium` 6 · `unknown→unknown` 67.
Tức 8 tin lừa đảo bị trả về `unknown` — người dùng sẽ thấy "chưa phát hiện dấu hiệu".

---

## Lượt 3 — L5 phân tích hội thoại (2026-07-30 22:20)

Tầng L5 phát hiện chiếm tài khoản người quen (`ml/src/chan_ml/thread.py`) đo trên
chính `CHAN-Dataset`, không phải trên case tự soạn.
Raw log: [`l5-thread-results.json`](l5-thread-results.json) ·
chạy lại: `.venv/bin/python -m chan_ml.evaluate_thread --dataset CHAN-Dataset --output eval/l5-thread-results.json`

| Chỉ số | Giá trị |
|---|---|
| Hội thoại chiếm tài khoản (positive) | 1.282 |
| Hội thoại hợp lệ (negative) | 2.229 |
| **Recall** | **0,0%** |
| **False positive** | **0,0%** |
| Positive không đủ lịch sử để so | **912 / 1.282** |

### Vì sao recall bằng 0 — và vì sao con số này vẫn được ghi nguyên

L5 so cách nhắn tin của một liên hệ **với chính họ trước đó**. Corpus không có
phần "trước đó":

- **1.132 / 1.282** hội thoại, kẻ gian hỏi tiền ngay **sau đúng 1 tin nhắn**;
  150 hội thoại còn lại hỏi tiền ngay từ tin đầu tiên. L5 cần tối thiểu 3 tin cũ
  → 912 hội thoại rơi thẳng vào `insufficient_history`.
- **0 / 1.282** hội thoại có nạn nhân đề nghị gọi điện hoặc gọi video, nên tín
  hiệu `ne_goi_thoai` không có cơ hội kích hoạt lần nào.
- Tín hiệu duy nhất từng bắt được là `yeu_cau_tien_dot_ngot` (370 lần).

**Kết luận trung thực: corpus này không kiểm được tính năng này.** Các hội thoại
bắt đầu *sau khi* tài khoản đã bị chiếm, trong khi tiền đề của L5 là luồng chat
có lịch sử từ *trước* lúc bị chiếm. Đây là giới hạn của dữ liệu, không phải bằng
chứng L5 đúng hay sai — và cũng không được trình bày như thể L5 đã được kiểm.

### Một quyết định đã đổi vì phép đo này

Lần đo đầu (trước khi sửa) cho recall 28,9% nhưng **false positive 19,4%** trên
2.229 hội thoại hợp lệ — vượt bar <15%. Nguyên nhân: chỉ cần "lần đầu người này
hỏi tiền" là đã cảnh báo `medium`, mà phần lớn hội thoại hợp lệ bị bắt là người
thân hỏi vay tiền thật.

Đã sửa: một mình `yeu_cau_tien_dot_ngot` không còn đủ để gắn nhãn cảnh báo, chỉ
còn hiện **các câu hỏi xác minh**. Đổi lại recall trên corpus này về 0 — đúng
như phân tích trên, vì corpus vốn không kích hoạt được hai tín hiệu mạnh. Lý do
chọn theo cost-of-error đã ghi trong spec §4: báo nhầm phá thứ sản phẩm không
xây lại được là **được tin**.

### L5 làm được gì trên case có lịch sử thật

Kiểm bằng test và bằng lời gọi thật lên production:

- Đoạn chat có lịch sử → đổi giọng văn + né gọi video: `high`, `doi_giong_van`
  0,91 + `ne_goi_thoai` 0,90.
- Cùng đoạn đó nhưng bạn thật hỏi vay tiền, giọng văn không đổi, nhận gọi video:
  **không** `high` (`test_the_same_request_from_the_real_friend_is_not_flagged_high`).

Hai case này là do nhóm dựng, nên chúng chứng minh *cơ chế chạy đúng*, **không**
chứng minh *tính năng hiệu quả ngoài đời*. Muốn kết luận được cần luồng chat có
lịch sử trước lúc bị chiếm — nhóm chưa có dữ liệu đó.

---

## Phân tích nguyên nhân *(bar đã đạt — ba vấn đề dưới đây vẫn phải ghi nhận)*

**1. Golden set 100% không chứng minh được bộ này đủ khó.**
20/20 và 136/136 nghe rất đẹp, nhưng cả 20 case đều do nhóm tự soạn và soạn khi đã
biết model bắt được gì. Bằng chứng: một bộ probe 36 câu soạn độc lập sau đó (không
nằm trong golden set) chỉ đạt **recall 22/24** và **3/12 báo nhầm** trên nhóm hợp
lệ — tệ hơn hẳn bộ 20 case. Kết luận trung thực: golden set hiện tại đang đo lại
thứ nhóm đã biết, chưa chạm được vùng chưa biết.

**2. Ba lỗi thật mà golden set không bắt được** (tìm bằng probe độc lập):

| Loại | Input | Kết quả | Vì sao đáng lo |
|---|---|---|---|
| Bỏ sót | "Anh chị đầu tư vào sàn này lợi nhuận 30%/tháng, đảm bảo không lỗ" | `unknown` 0.17 | Trọng số `loi_ich_bat_thuong` chỉ 0.08 — cộng tối đa vẫn không chạm ngưỡng `medium` 0.35 |
| Bỏ sót | "Bác cài ứng dụng dịch vụ công theo link này để cập nhật định danh mức 2" | `unknown` (scam_conf 0.33) | Đúng kịch bản app dịch vụ công giả đang phổ biến ngoài đời |
| **Báo nhầm `high`** | "Nhà trường thông báo học phí học kỳ 2 là 3 triệu, phụ huynh nộp tại phòng kế toán" | `high` 0.70 · `mao_danh_tham_quyen` | Tin nhắn hợp lệ bị hét lên mức cao nhất |

**3. Vấn đề cấu trúc của L4 policy.** Với `scam_confidence = 0`, có **21 tổ hợp dấu
hiệu không bao giờ chạm nổi `medium`** dù confidence = 1.0, kể cả tổ hợp 3 dấu
hiệu — ví dụ `tk_ca_nhan + cai_app_ngoai` tối đa 0.30 < 0.35. Nghĩa là trên thực tế
`scam_confidence` đang gánh gần hết quyết định, còn bộ trọng số 8 dấu hiệu gần như
không quyết định được gì. Vấn đề này đã ghi trong
[`docs/CHAN-ARCHITECTURE.md`](../docs/CHAN-ARCHITECTURE.md) §6 ngay lúc hiện thực và
nhóm chốt **không tự ý sửa trọng số khi chưa có golden set từ dữ liệu thật**.

**Failure nguy hiểm nhất:** báo nhầm `high` cho tin nhắn nhà trường thông báo học
phí. Người dùng mục tiêu là người lớn tuổi. Nếu CHẮN hét "nhiều dấu hiệu lừa đảo"
vào một tin nhắn thật của trường, họ sẽ không nộp học phí — và lần sau sẽ không
còn tin cảnh báo của CHẮN nữa. Sai theo hướng này đắt hơn bỏ sót một tin lừa đảo,
vì nó phá đúng thứ sản phẩm cần nhất: được tin.

**Hành động tiếp theo:**
1. Bổ sung vào golden set các case hợp lệ dễ bị báo nhầm (thông báo trường học,
   viện phí, biến động số dư, vay mượn giữa người quen) — hiện chỉ có 2 case loại này.
2. Hiệu chỉnh trọng số L4 hoặc retrain khi có dữ liệu thật — **sau** khi bar đã
   chốt, và ghi thành lượt đo riêng để so sánh được.
3. Viết case ngược cho lớp ② và ③ (mỗi lớp hiện chỉ 2 case, đều pass ngay lượt đầu).

## Chạy lại

Toàn bộ lệnh nằm trong [`../codebase/ml/README.md`](../codebase/ml/README.md).
Checksum model và các file kết quả: [`../codebase/ml/ARTIFACTS.json`](../codebase/ml/ARTIFACTS.json).
