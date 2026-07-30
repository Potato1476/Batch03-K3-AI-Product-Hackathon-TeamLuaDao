# AI SPEC — CHẮN · Nhóm LuaDao · Zone [X]

Hướng: [ ] A — VLearn  [ ] B — Trợ lý Học viên  [x] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

> Hạn cứng: commit trước 23:59 ngày 1. Quality bar (§7) chốt từ thời điểm nộp, không sửa sau đó.
> Hướng dẫn viết từng mục: `../02-guide.md`. Rubric: `../04-rubric.md`.

> **⚠️ TRẠNG THÁI FILE — đọc trước khi nộp.**
> §4, §4b, §5, §6, §7 đã điền, mô tả đúng sản phẩm đang chạy trong `codebase/` và
> kiểm chứng được bằng file/dòng code cụ thể.
> **§1, §2, §3, §8, §9 chưa điền và không ai điền hộ được** — chúng cần khảo sát
> người thật, số mining đếm được, tên thành viên và feedback thật. Bịa số vào đây
> vi phạm luật của khoá (`04-rubric.md`: "số liệu bị chỉnh sửa hoặc che giấu sẽ
> không được tính") và nguy hiểm hơn là bỏ trống, vì bỏ trống chỉ mất điểm mục đó.
> Xem `evidence/README.md` để biết cần thu gì.

## §1. User & Job

> **CHƯA CÓ — cần cả nhóm làm trước 23:59 N1.** Đây là khối điểm lớn nhất còn bỏ ngỏ
> (R1 = 15/75 điểm). Thư mục `evidence/` hiện chỉ có README, không có một dòng
> bằng chứng nào.

- **Job executor + workflow** (đính kèm worksheet JTBD / ảnh sơ đồ): TODO
- **Core JTBD** (không tên sản phẩm/AI trong câu): TODO
- **Problem statement** (KHÔNG chữ AI): TODO
- **Evidence** — chuẩn A (khảo sát ≥20 người ngoài nhóm, ≥50% xác nhận) và/hoặc chuẩn B (số mining đếm được + phương pháp đếm kiểm lại được). Log đầy đủ trong repo:
  - Số liệu mining / kết quả khảo sát (n = ?, % xác nhận): TODO
  - Phương pháp đếm (ai đếm, đếm trên tập nào, tiêu chí gán nhãn): TODO
  - Log đầy đủ: `evidence/` — **hiện đang trống**

  **≥5 quote/ví dụ nguyên văn + nguồn:**

  | # | Quote nguyên văn | Nguồn (file/dòng hoặc người + vai) |
  |---|---|---|
  | 1 | | |
  | 2 | | |
  | 3 | | |
  | 4 | | |
  | 5 | | |

## §2. Impact & quyết định chọn

> **CHƯA CÓ — cần cả nhóm.** Bảng này phải có con số lấy từ §1.

**Bảng impact ≥3 ứng viên:**

| Ứng viên | Bao nhiêu người | Tần suất | Tốn gì mỗi lần | Khả thi trong 1,5 ngày | Chọn/Loại |
|---|---|---|---|---|---|
| A | | | | | |
| B | | | | | |
| C | | | | | |

- **Ứng viên ĐÃ LOẠI + vì sao** (giữ lại, không xoá): TODO
- **Ứng viên CHỌN + vì sao (bằng số)**: TODO

## §3. Giải pháp tương tự đã nghiên cứu

> **CHƯA CÓ.** Guide §2.2: chia người, 15'/người. Gợi ý ứng viên để tra: nút "Báo
> cáo lừa đảo" trong app ngân hàng VN · tinnhiemmang.vn · checkscam.vn ·
> Google Messages spam protection · Truecaller. Phải tự mở ra xem rồi ghi, không
> chép mô tả.

| Sản phẩm | Flow của họ | Đáng học | Đáng né | Mình khác gì |
|---|---|---|---|---|
| [Sản phẩm 1] | | | | |
| [Sản phẩm 2] | | | | |

## §4. Thiết kế

- **Lát cắt MỘT CÂU** (1 user · 1 việc · 1 quyết định AI · 1 kết quả):

  > Khi **một người lớn tuổi** nhận được một tin nhắn đáng ngờ và **đang phân vân
  > có làm theo hay không**, CHẮN **chấm tin nhắn đó theo 8 dấu hiệu thao túng**
  > và trả về **một mức cảnh báo kèm câu hỏi để họ tự hỏi lại người gửi**, trước
  > khi họ chuyển tiền hoặc đọc mã xác nhận.

  Khớp bản build: [`apps/web/src/App.tsx`](codebase/apps/web/src/App.tsx) (màn nhập →
  màn kết quả), quyết định AI ở
  [`detection/src/chan_detection/main.py`](codebase/detection/src/chan_detection/main.py).

- **Non-goals (≥3 thứ KHÔNG build):**
  1. **Không chặn giao dịch.** CHẮN không dừng được lệnh chuyển tiền, không gọi
     ngân hàng, không khoá gì cả. Nó chỉ nói ra thứ nó thấy; người dùng vẫn là
     người bấm nút cuối cùng.
  2. **Không có nhãn "An toàn".** Enum `risk` chỉ có `high`/`medium`/`unknown`
     (bất biến I6 — cưỡng chế bằng `forbidden_labels` trong
     [`rules/bundle.json`](codebase/rules/bundle.json), có test chặn).
  3. **Không giám sát ngầm.** Không đọc tin nhắn nền, không tự gửi cảnh báo cho
     người thân nếu chưa được xác nhận trên chính máy người được bảo vệ (I5).
  4. **Không lưu nội dung tin nhắn ở server.** Bảng `analyses` không có cột chứa
     text; chỉ lưu hash + điểm + mã dấu hiệu (I2).
  5. **Không tra cứu danh tính người dùng.** Lookup dùng k-anonymity theo 5 ký tự
     đầu của hash, server không biết đang tra gì (I4).

  Bản build không vi phạm mục nào ở trên; các bất biến được liệt kê trong
  [`docs/CHAN-ARCHITECTURE.md`](docs/CHAN-ARCHITECTURE.md) §0.

- **Mức prototype nhắm tới:** [ ] Sketch [ ] Mock [x] Working
  - **Phần THẬT:** bộ phân loại 8 dấu hiệu (n-gram + Logistic Regression đa nhãn,
    artifact `ml/artifacts/chan-signal-model.joblib`) · L4 risk policy · chuẩn hoá
    L0 + luật L1 trên máy · ẩn danh hoá L2 · Gateway `/v1/analyze` · OCR Tesseract
    `vie+eng` tự host · lookup hash-only · Web PWA đầy đủ luồng · daily retraining +
    model registry. Đã deploy chạy thật: https://chan-flame.vercel.app
  - **Phần MOCK / chưa nối:** tầng LLM L3 và pgvector similarity (kiến trúc có
    chỗ, chưa nối) · OpenPhish connector (khoá mặc định, chỉ bật khi có quyền bằng
    văn bản) · client Android · màn "Bảo vệ & riêng tư" (guardian) là UI tĩnh, chưa
    có luồng ghép cặp thật.
    *(Khớp với bảng THẬT/MOCK trong [`codebase/README.md`](codebase/README.md).)*

- **Automation:** [x] augment [ ] conditional [ ] automate
  - **Lý do theo cost-of-error.** Sai theo hướng **báo nhầm** thì người lớn tuổi
    không dám làm một việc hợp lệ (không nộp học phí, không nhận tiền) và **mất
    niềm tin vào chính cảnh báo** — lần sau họ bỏ qua cả cảnh báo đúng. Sai theo
    hướng **bỏ sót** thì họ mất tiền, gần như không lấy lại được. Cả hai hướng sai
    đều đắt và người chịu hậu quả không phải nhóm build. Vì vậy CHẮN **không tự
    quyết thay**: nó chỉ ra dấu hiệu, kèm câu hỏi để người dùng tự kiểm chứng qua
    kênh chính thức, và luôn nói rõ "chưa phát hiện dấu hiệu" **không** có nghĩa
    là an toàn.
  - **Một ngoại lệ có chủ ý:** với nội dung chứa hoặc đòi mã OTP, hệ thống **tự
    quyết** mức `high` ngay trên máy và không gửi gì lên server (bất biến I1,
    [`apps/web/src/engine.ts`](codebase/apps/web/src/engine.ts) `localHigh`). Ở
    case này cost-of-error một chiều: không có tình huống hợp lệ nào cần người lạ
    biết mã OTP của bạn.

### §4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR)

| Nguyên tắc | Áp cụ thể vào đâu trong prototype (file/màn hình) |
|---|---|
| **G1 — Làm rõ hệ thống làm được gì** | Màn hình đầu hỏi thẳng "BÁC MUỐN KIỂM TRA GÌ?" với đúng 2 việc CHẮN làm được: kiểm tra tin nhắn, tra cứu tài khoản/SĐT. Không có ô chat mở để người dùng tưởng hỏi được mọi thứ. `App.tsx` → `Home` |
| **G2 — Làm rõ nó làm tốt đến đâu** | Mọi màn kết quả "không thấy gì" đều kèm câu giới hạn: "Không có báo cáo **không có nghĩa là an toàn tuyệt đối**. Kẻ xấu có thể dùng một số điện thoại chưa từng bị báo cáo." `App.tsx` → `ClearLookupResult`, `.disclaimer` |
| **G10 — Thu hẹp phạm vi khi nghi ngờ** | Khi cửa lọc L1 trên máy không thấy dấu hiệu nào, app **không** hiện kết quả như đã chấm xong. Nó hiện "Máy chưa thấy dấu hiệu nào — tin nhắn chưa được gửi đi chấm sâu. Đây chưa phải kết luận" kèm nút escalate. `App.tsx` → `Result` (`localOnly`), `engine.ts` → `localUnknown` |
| **G11 — Giải thích vì sao** | Màn kết quả liệt kê đủ 8 tiêu chí, đánh dấu tiêu chí nào trúng, và **trích nguyên văn câu trong tin nhắn** làm bằng chứng cho từng dấu hiệu (`<blockquote>`), kèm tin nhắn gốc ngay đầu màn hình để đối chiếu. `App.tsx` → `Result`, `CheckedMessage` |
| **G9 — Sửa dễ dàng** | Chữ đọc từ ảnh (OCR) đổ vào ô soạn thảo để người dùng sửa trước khi bấm kiểm tra, kèm nhắc "Bác xem lại chữ trước khi kiểm tra". Ở màn kết quả có nút "Kiểm tra kỹ hơn" để chấm lại sâu hơn. `App.tsx` → `InputScreen.handleImage`, `Result.onDeepCheck` |
| **PAIR — Errors + Graceful Failure** | Mỗi loại lỗi có đường lui riêng chứ không dùng chung một thông báo: mất micro → "dán chữ thay"; ảnh quá 6MB → "chọn ảnh nhỏ hơn"; trình duyệt không xử lý giọng nói cục bộ → "gửi ảnh thay"; mất mạng → nói rõ phần nào vẫn chạy được trên máy. `App.tsx` → `errorCopy`, `ErrorBox` |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

**4 lớp chỗ khó:**

| Lớp | Tên lớp | Cụ thể hoá trong bài của nhóm |
|---|---|---|
| ① | Không có căn cứ / model không biết | Tin nhắn quá ngắn, cụt, hoặc là ảnh chụp mờ OCR ra vài chữ rời. Không có gì để chấm nhưng người dùng vẫn đang chờ một câu trả lời — và câu trả lời sai nguy hiểm nhất ở đây là "không sao đâu". |
| ② | Mơ hồ, độ tin thấp | Tin nhắn mạo danh người quen ("cháu là Tuấn, máy cháu hỏng nên dùng số này") — đọc lên giống hệt tin nhắn thật của người thân. Model có chút tín hiệu nhưng không đủ để khẳng định. |
| ③ | Đòi hỏi ngoài phạm vi | Người dùng hỏi thứ CHẮN không được phép trả lời: "làm sao đòi lại 20 triệu vừa bị lừa?", "có nên đầu tư sàn coin này không?". Trả lời bừa ở đây là tư vấn pháp lý/tài chính không có thẩm quyền. |
| ④ | Case đặc thù domain | Tin nhắn **thật** trông giống tin lừa đảo: SMS biến động số dư ngân hàng, thông báo học phí của trường, và tin cảnh báo của Công an (chứa đúng những từ khoá mà model học để nhận diện mạo danh). Báo nhầm ở đây phá niềm tin nhanh nhất. |

**Kịch bản (≥8, phủ đủ 4 lớp):**

| # | Lớp | Input / tình huống | Hành vi mong muốn của hệ thống |
|---|---|---|---|
| 1 | ① | Tin nhắn cụt: "Alo / 123456 / ???" | Trả `unknown`, `signals = []`. Nói rõ chưa đủ căn cứ, **không** nói an toàn. Hỏi lại một câu định hướng: tin đến từ đâu, có đòi bấm link/chuyển tiền/đọc mã không. (golden `G09`) |
| 2 | ① | Cửa lọc trên máy không khớp luật nào → chưa có gì để chấm | Không hiện như đã chấm xong. Hiện "Máy chưa thấy dấu hiệu nào — chưa gửi đi chấm sâu" + nút "Kiểm tra kỹ hơn". (`App.tsx` → `Result` khi `localOnly`) |
| 3 | ② | "Cô ơi cháu là Tuấn đây, điện thoại cháu bị hỏng nên dùng số này." | Trả `medium` chứ không `high`. Không khẳng định là lừa đảo; đưa câu hỏi kiểm chứng: gọi lại số cũ của người đó để xác nhận. (golden `G11`) |
| 4 | ② | Model ra `medium` nhưng không nêu được dấu hiệu cụ thể nào | Vẫn phải hiện đủ 8 tiêu chí với trạng thái "không trúng", và phần giải thích không được bịa lý do. *(Hiện `G11` đang rơi đúng vào đây — xem `eval/results.md`.)* |
| 5 | ③ | "Tôi vừa bị lừa mất 20 triệu, làm sao đòi lại tiền từ ngân hàng?" | Không hứa đòi được tiền, không tư vấn thủ tục pháp lý. Hướng dẫn liên hệ Công an và tổng đài chính thức của ngân hàng. (golden `G13`) |
| 6 | ③ | "Có nên đầu tư vào sàn coin ABC cam kết lãi 30%/tháng không?" | Không khuyên nên/không nên đầu tư. Chỉ ra dấu hiệu cam kết lợi nhuận bất thường và nhắc tự kiểm chứng. (golden `G14`) |
| 7 | ④ | SMS thật: "Vietcombank: Số dư TK …+1,000,000 VND. Ref: Luong T7." | **Không** báo động. `unknown`, score < 0.20. (golden `G15`) |
| 8 | ④ | Tin cảnh báo thật của Công an, chứa đúng từ khoá "mạo danh công an", "chuyển tiền" | Đọc được ngữ cảnh bảo vệ, **không** đọc ngược thành tin mạo danh. `unknown`. (golden `G16`) |
| 9 | ④ | Thông báo học phí thật của nhà trường có số tiền | Không được báo `high`. *(**Hiện đang FAIL** — trả `high` + `mao_danh_tham_quyen`. Ghi nhận trong `eval/results.md` là failure nguy hiểm nhất.)* |
| 10 | ①/I1 | Tin nhắn chứa hoặc đòi mã OTP | Chặn cứng ngay trên máy, mức `high`, **không gửi byte nào lên server**, kèm câu "Đừng đọc mã cho bất kỳ ai". (golden `G04`, `G20`) |
| 11 | hạ tầng | Máy chủ CHẮN không phản hồi | Không im lặng, không trả kết quả giả. Hiện lỗi riêng "Chưa kết nối được hệ thống" + nút thử lại, giữ nguyên nội dung người dùng đã nhập. (`errorCopy.backend`) |
| 12 | hạ tầng | Mất mạng | Banner nói rõ phần nào vẫn chạy: "Mất mạng · kiểm tra trên máy vẫn hoạt động"; tra cứu cộng đồng thì báo không dùng được. (`errorCopy.offline`) |

## §6. Bốn đường đi của trải nghiệm

| Đường đi | Hệ thống làm gì | Thể hiện ở đâu trong prototype |
|---|---|---|
| **Happy path** | Người dùng dán/chụp/đọc tin nhắn → chấm → banner đỏ "Nhiều dấu hiệu lừa đảo" + hướng dẫn "Đừng chuyển tiền. Đừng đọc mã OTP." + trích nguyên văn câu thao túng + câu hỏi để hỏi lại người gửi + số hotline chính thức để tự gọi | `App.tsx` → `Result` (risk `high`) · demo: golden `G01`, `G03` |
| **Low-confidence (②)** | Banner vàng "Cần kiểm tra thêm" + "Hãy dừng lại và tự gọi kênh chính thức". Không khẳng định lừa đảo | `App.tsx` → `riskCopy.medium` · golden `G11`, `G12` |
| **Failure / không căn cứ (①)** | Hai trường hợp tách bạch: (a) model đã chấm nhưng không đủ dấu hiệu → "Chưa phát hiện dấu hiệu" + nhắc đây không phải kết luận an toàn; (b) cửa lọc trên máy giữ lại, chưa chấm → "Máy chưa thấy dấu hiệu nào — chưa gửi đi chấm sâu" + nút escalate | `App.tsx` → `riskCopy.unknown` và `localOnlyCopy` |
| **Correction (user sửa)** | Chữ OCR ra được đổ vào ô soạn thảo sửa được trước khi chấm; sau khi có kết quả vẫn bấm "Kiểm tra kỹ hơn" để chấm lại, hoặc "Kiểm tra tin khác" để làm lại từ đầu | `App.tsx` → `InputScreen.handleImage`, `Result.onDeepCheck` |
| **Bị đòi ngoài phạm vi (③)** | Không trả lời câu hỏi pháp lý/đầu tư. Chỉ chấm dấu hiệu trong nội dung và đẩy về kênh chính thức | golden `G13`, `G14` |
| **Case đặc thù domain (④)** | Có lớp "ngữ cảnh bảo vệ" hạ confidence khi câu mang nghĩa cảnh báo thay vì yêu cầu (`chan_ml/protective_context.py`) | golden `G15`, `G16` |

## §7. Kiểm thử

**Chiều chất lượng + định nghĩa kiểm chứng được** (người ngoài nhóm chấm phải ra cùng kết quả):

| Chiều chất lượng | Định nghĩa PASS (kiểm chứng được) | Cách chấm |
|---|---|---|
| **C1 · Mức rủi ro đúng** | `risk` trả về khớp mức kỳ vọng của case; nếu kỳ vọng ghi khoảng điểm thì `score` phải nằm trong khoảng | Máy chấm, `chan-evaluate-workbook` |
| **C2 · Dấu hiệu đúng** | Mọi signal code kỳ vọng đều có trong `signals` trả về (signal thừa không tính fail — bộ 8 dấu hiệu là đa nhãn) | Máy chấm |
| **C3 · Không trấn an sai** | Output không bao giờ chứa nhãn "an toàn"/"safe"/"ok"/"clean"; `risk` chỉ nhận `high`/`medium`/`unknown` | Test tự động trên `forbidden_labels` |
| **C4 · OTP không rời máy** | Case chứa/đòi OTP phải cho verdict tại L1 (`engine_version = l1-local`), không phát sinh request `/v1/analyze` | Test tự động `engine.test.ts` |
| **C5 · Bền với nhiễu chính tả** | 8 biến thể tự sinh mỗi case (thiếu dấu, sai 1 ký tự, chèn dấu phân tách, đổi khoảng trắng) giữ nguyên mức rủi ro của case gốc | Máy chấm, seed cố định `20260731` |

- **Golden set:** 20 case — 2 case/lớp chỗ khó + 8 case thường + 4 case hiếm. File:
  [`eval/golden-set.md`](eval/golden-set.md).
  **Chưa đạt mục "≥10 case từ chatlog thật": hiện 0/10.** Chatlog VLearn được cấp
  không chứa nội dung lừa đảo (tìm 11.383 dòng, 0 kết quả cho "lừa đảo/OTP/chuyển
  tiền/mạo danh/trúng thưởng"), nên toàn bộ 20 case là nhóm tự soạn. Ghi nhận đúng
  như vậy thay vì gắn nhãn nguồn không kiểm lại được.

- **Quality bar** *(chốt từ 23:59 N1, giữ nguyên sau đó)*:
  > "Đạt khi **≥90% golden set qua (≥18/20)**, **và** trên bộ test hợp lệ của nhóm:
  > **recall nhóm lừa đảo ≥ 90%**, **false positive nhóm hợp lệ < 15%**, **và**
  > không case nào bị gắn nhãn trấn an."

  Ba ngưỡng recall/FP/nhãn-cấm đã nằm trong code từ trước khi chốt bar
  (`chan_ml/evaluate_product.py` → `acceptance`; `rules/bundle.json` →
  `forbidden_labels`), không phải đặt lùi cho khớp kết quả.

- **Kết quả các lượt chạy:** bảng đầy đủ trong [`eval/results.md`](eval/results.md)

| Lượt | Thời điểm | Thay đổi gì so với lượt trước | % pass | Đối chiếu bar |
|---|---|---|---|---|
| 1 | 2026-07-30 11:38 | baseline (model typo-robust, bundle `rb-…4`) | 20/20 = 100% · recall 0.936 · FP 0.082 | Đạt |
| 2 | 2026-07-30 13:57 | bundle `rb-…5`: thêm rule escalation `risk_surface`, sửa va chạm "gấp"/"gặp" | 20/20 = 100% · recall 0.936 · FP 0.082 | Đạt |

> **Đạt bar không có nghĩa là xong.** `eval/results.md` ghi rõ ba vấn đề bộ golden
> set không bắt được, trong đó có một báo nhầm `high` trên tin nhắn học phí hợp lệ.

## §8. Phân công & kế hoạch

> **CHƯA CÓ — chỉ nhóm điền được.** Bảng thành viên trong
> [`README.md`](README.md) cũng đang trống; R7 trừ điểm nếu ghi "cả nhóm".

- **Phân công có tên** (bảng đầy đủ trong [README.md](README.md)): spec / evidence / prompt / code / demo
- **Willing users (≥3 tên)** + kế hoạch vòng validation CP5:

  | Tên | Vai / vì sao là đúng người | Ai liên hệ | Đã test chưa |
  |---|---|---|---|
  | | | | ☐ |
  | | | | ☐ |
  | | | | ☐ |

  3 câu hỏi hỏi user: 1) TODO 2) TODO 3) TODO — người log: TODO
- **Multi-prototype (nếu làm):** trục khác biệt của ≥2 phương án + lý do chọn: TODO

## §9. Changelog

> Hai dòng dưới là thay đổi kỹ thuật đã thực sự xảy ra hôm nay, có commit và có số
> đo kèm theo. **Chưa có dòng nào bắt nguồn từ feedback người dùng** vì vòng
> validation chưa chạy — R6 (8 điểm) yêu cầu ≥1 thay đổi từ feedback thật.

| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| 2026-07-30 | Thêm rule escalation `risk_surface` vào `rules/bundle.json`; màn kết quả tách bạch "cửa lọc giữ lại" với "model đã chấm", thêm nút "Kiểm tra kỹ hơn" | Tin nhắn lừa đảo diễn đạt ngoài danh mục regex bị trả `unknown` tại chỗ mà không bao giờ tới model, hiển thị y hệt kết quả đã chấm. Kiểm chứng: "con là nhân viên ngân hàng, tài khoản của bác đang bị khoá…" bị cửa lọc chặn trong khi model chấm `medium` |
| 2026-07-30 | Sửa luật `time_pressure`: "gấp" và "gặp" trùng nhau sau khi L0 bỏ dấu | Mọi tin nhắn hẹn gặp đều kích hoạt tín hiệu thúc ép thời gian → báo nhầm trên loại tin nhắn đời thường phổ biến nhất. Có test chặn hồi quy trong `ml/tests/test_local_rules.py` |
| | *(chờ vòng validation CP5)* | |
