# CHẮN — Trợ lý chống lừa đảo
### Nhóm LuaDao · Demo CP6

> Luật tự áp: **không có bằng chứng thì không có slide.** Mọi con số dưới đây
> chạy lại được bằng lệnh ghi trong `eval/` và `evidence/`.

> **File này là kịch bản nói, không phải slide chiếu.** Slide đã dựng là
> [`demo-slides.pdf`](demo-slides.pdf), sinh từ [`slides/build_deck.py`](slides/README.md)
> — 6 trang tối giản, mỗi trang một ý, trang cuối là link demo. Trang 5 dưới đây
> (*User thật nói gì*) **chưa có trong bộ slide** vì vòng validation chưa chạy;
> slide 05 hiện là *Số đo*. Khi có quote thật thì thêm trang vào `build_deck.py`.

| Trang | Thời lượng | Người nói |
|---|---|---|
| 1. User & Job | 45" | *(điền)* |
| 2. Vì sao chọn tính năng này | 45" | *(điền)* |
| 3. Giải pháp & demo live | 2' | *(điền)* |
| 4. Kết quả đo | 45" | *(điền)* |
| 5. User thật nói gì | 45" | *(điền)* |
| 6. Nếu có thêm 1 tuần | 30" | *(điền)* |

---

## 1. User & Job · 45"

**Ai:** người 55+ dùng smartphone nhưng ít kinh nghiệm số, **đang cầm máy đọc một
tin nhắn vừa đến**, phải quyết trong vài phút.

**Việc họ đang cố làm** *(không có chữ AI)*:
> Biết chắc tin nhắn này thật hay giả **trước khi làm theo** — để không mất tiền,
> và cũng không phải phiền con cháu mỗi lần nghi ngờ.

**Hôm nay họ làm gì, và nó hỏng ở đâu:** gọi con cháu (phải chờ, ngại phiền, đêm
không gọi được) · tự tra mạng (không biết tra gì) · gọi tổng đài ngân hàng (chờ
lâu) · đoán rồi làm liều.

**Con số:**
> **15.840 hội thoại lừa đảo · 181.943 tin nhắn** đã mining, trong đó **6.391 từ
> 6 nguồn public dẫn tên được** (PhishVN Mendeley · ChongLuaDao.vn · VNCERT SMS
> Spam · ConScamBench-278 · Zenodo SCC · EMSCAD).
> Script đếm: `evidence/scripts/mine_chan_dataset.py`

**Nói thẳng luôn nếu bị hỏi:** corpus này cân bằng nhân tạo (mỗi kịch bản ~427
hội thoại, tỉ lệ mất tiền đúng 33,3% ở mọi nhóm), nên nó chứng minh **các mẫu
lừa đảo tồn tại và trông thế nào**, không chứng minh tần suất ngoài đời.

---

## 2. Vì sao chọn tính năng này · 45"

| Ứng viên | Số hội thoại | Quyết định |
|---|---|---|
| **A. Mạo danh cơ quan chức năng** | 2.137 | **CHỌN** |
| B. Chiếm tài khoản người quen | 1.282 | Làm thêm cuối N1 (L5) |
| C. Mạo danh ngân hàng | 851 | Gộp vào A — cùng cơ chế |
| **D. Dụ đầu tư / việc nhẹ lương cao** | 854 | **LOẠI** |

**Vì sao loại D — có số đứng sau, không phải cảm tính:**
> Model trả `unknown` cho *"đầu tư sàn này lợi nhuận 30%/tháng, đảm bảo không
> lỗ"*. Trọng số `loi_ich_bat_thuong` chỉ **0,08**; cộng tối đa vẫn không chạm
> ngưỡng `medium` **0,35**. Kịch bản này còn kéo dài nhiều phiên — ngoài tầm một
> lát cắt 1,5 ngày.

**Vì sao chọn A:** nhiều nhất (gấp 2,5 lần D), gộp được C, và quyết định gọn
trong **một tin nhắn** nên demo được trong 5 phút.

---

## 3. Giải pháp & demo live · 2'

**Lát cắt một câu:**
> Khi **một người lớn tuổi** nhận tin nhắn đáng ngờ và đang phân vân có làm theo
> hay không, CHẮN **chấm tin nhắn theo 8 dấu hiệu thao túng** và trả về **một mức
> cảnh báo kèm câu hỏi để họ tự hỏi lại người gửi** — trước khi chuyển tiền hoặc
> đọc mã OTP.

**Automation = augment.** Cost-of-error hai chiều đều đắt: báo nhầm → cụ không
dám làm việc hợp lệ và **mất niềm tin vào cảnh báo**; bỏ sót → mất tiền, gần như
không lấy lại. Nên CHẮN **không quyết thay** — chỉ ra dấu hiệu + câu hỏi để tự
kiểm chứng qua kênh chính thức. *Một ngoại lệ:* tin có OTP thì chặn cứng ngay
trên máy, vì không có tình huống hợp lệ nào cần người lạ biết mã của bạn.

### Demo trực tiếp — https://chan-flame.vercel.app

**Case chuẩn:**
> *"Tôi là cán bộ công an. Bác phải chuyển tiền xác minh trước 17h hôm nay và
> không được nói với người nhà."*
> → `high` · trúng `mao_danh_tham_quyen` + `ap_luc_thoi_gian` · trích nguyên văn
> câu thao túng · kèm hotline chính thức để **tự gọi**.

**Case chỗ khó — lỗi đã tìm ra và đã sửa, không giấu:**
> *"Chào bác, con là nhân viên ngân hàng, tài khoản của bác đang bị khoá…"*
> Sáng nay câu này **pass âm thầm**: cửa lọc L1 trên máy không khớp regex nào nên
> trả `unknown` tại chỗ và **model không bao giờ được gọi** — màn hình hiện y hệt
> như đã chấm xong.
> Đã sửa: thêm rule escalation + màn kết quả nay **phân biệt** "cửa lọc giữ lại"
> với "model đã chấm", kèm nút *Kiểm tra kỹ hơn*.
> → giờ trả `medium`.

---

## 4. Kết quả đo · 45"

**Quality bar chốt 23:59 N1:** ≥90% golden set (≥18/20) **và** recall ≥90% **và**
false positive <15% **và** không nhãn trấn an nào.

| Phép đo | Kết quả | Bar |
|---|---|---|
| Golden set 20 case | **20/20 = 100%** | ≥90% ☑ |
| 136 biến thể nhiễu chính tả | **136/136 = 100%** | — ☑ |
| Recall trên 125 tin lừa đảo | **93,6%** | ≥90% ☑ |
| False positive trên 73 tin hợp lệ | **8,2%** | <15% ☑ |

**Đạt bar không có nghĩa là xong** — ba thứ phải nói ra:

1. **20/20 không chứng minh bộ case đủ khó.** Probe 36 câu soạn độc lập sau đó
   chỉ được **22/24 recall** và **3/12 báo nhầm** — tệ hơn hẳn bộ 20 case. Golden
   set đang đo lại thứ nhóm đã biết.
2. **Failure nguy hiểm nhất:** *"Nhà trường thông báo học phí học kỳ 2 là 3 triệu,
   phụ huynh nộp tại phòng kế toán"* → **`high` + `mao_danh_tham_quyen`**. Tin
   nhắn thật bị hét lên mức cao nhất. Với người 60 tuổi, sai kiểu này đắt hơn bỏ
   sót: họ không nộp học phí, và lần sau không tin cảnh báo nữa.
3. **L5 (phát hiện chiếm tài khoản) đo trên 1.282 hội thoại thật: recall 0.** Vì
   1.132/1.282 hội thoại hỏi tiền ngay sau 1 tin nhắn và 0 hội thoại nào nạn nhân
   đòi gọi video — **corpus không có phần "trước đó" để so**. Ghi nguyên, và L5
   được khai là **ngoài lát cắt, chưa validate**.

---

## 5. User thật nói gì · 45"

> ⚠️ **TRANG NÀY CHƯA CÓ NỘI DUNG — điền sau vòng validation sáng CP5.**
> Cần ≥2 quote nguyên văn kèm tên/vai + 1 thay đổi đã làm từ feedback.
> Kịch bản chạy vòng validation: [`validation/session-script.md`](validation/session-script.md)

- Quote 1 (tên/vai):
- Quote 2 (tên/vai):
- Thay đổi đã làm từ feedback:

---

## 6. Nếu có thêm 1 tuần · 30"

1. **Hiệu chỉnh lại trọng số L4.** Đo được: với `scam_confidence = 0` có **21 tổ
   hợp dấu hiệu không bao giờ chạm nổi `medium`** dù confidence = 1.0 — kể cả tổ
   hợp 3 dấu hiệu. Nghĩa là 8 trọng số hiện gần như không quyết định gì, một mình
   `scam_confidence` gánh hết.
2. **Golden set từ dữ liệu thật.** Hiện 0/20 case đến từ chatlog thật; và corpus
   training chỉ có **8,1% câu khác nhau** trong nhóm chiếm tài khoản — model dễ
   thuộc template thay vì hiểu kịch bản.
3. **Thu luồng chat có lịch sử trước lúc bị chiếm**, thứ duy nhất kiểm được L5.

**Bài học lớn nhất:**
> Bug tệ nhất hôm nay không phải model đoán sai — mà là màn hình **trình bày một
> quyết định chưa hề xảy ra y như một quyết định đã xảy ra**. Người dùng không
> phân biệt được "chưa kiểm" và "kiểm rồi không thấy gì", trong khi khoảng cách
> giữa hai câu đó chính là toàn bộ giá trị của sản phẩm.

---

## Cả nhóm phải trả lời được

- **"Augment hay automate — vì sao?"** → augment; cost-of-error hai chiều đều
  đắt và người chịu hậu quả không phải nhóm build. Ngoại lệ OTP chặn cứng.
- **"Failure nguy hiểm nhất?"** → tin nhắn học phí thật bị gắn `high`.
- **"Phần bạn làm là gì?"** → mỗi người mở đúng file có tên mình trong
  `README.md` và giải thích được.

## Backup demo

- [ ] Screenshot/video ngắn phòng live hỏng — lưu tại `codebase/demo-backup/`
