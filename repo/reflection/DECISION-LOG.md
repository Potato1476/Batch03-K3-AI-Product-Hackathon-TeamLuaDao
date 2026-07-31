# Nhật ký quyết định — nguyên liệu viết reflection

> Đây là **dữ kiện**, không phải bài học. Mỗi người chọn một mục mình dính trực
> tiếp, rồi tự viết ra mình hiểu được gì. Rubric hỏi "một bài học từ case fail
> của chính nhóm" — dưới đây là các case fail thật, kèm bằng chứng mở lại được.

Mọi con số đều chạy lại được bằng lệnh ghi trong `eval/` và `evidence/`.

---

## 1. Cửa lọc trả `unknown` mà model chưa từng được gọi

**Tin là gì trước đó:** model chấm mọi tin nhắn người dùng gửi lên.

**Đo được:** cửa lọc L1 trên máy chỉ gọi server khi tin nhắn khớp một trong ~18
regex. Không khớp cái nào thì trả `unknown` tại chỗ, và màn hình hiện **y hệt**
như khi model đã chấm xong. Kiểm chứng: *"Chào bác, con là nhân viên ngân hàng,
tài khoản của bác đang bị khoá…"* bị chặn ở cửa lọc, trong khi model chấm
`medium`.

**Đã đổi:** thêm rule escalation `risk_surface`; màn kết quả tách bạch "cửa lọc
giữ lại" với "model đã chấm", thêm nút *Kiểm tra kỹ hơn*.

**Chỗ đáng nghĩ:** bug này không nằm trong model. Nó nằm ở chỗ **giao diện trình
bày một quyết định chưa xảy ra y như một quyết định đã xảy ra**.

`docs/CHAN-ARCHITECTURE.md` §0 (hiệu chỉnh I3) · `codebase/apps/web/src/engine.ts`

---

## 2. "gấp" và "gặp" là cùng một từ sau khi bỏ dấu

**Tin là gì trước đó:** bỏ dấu tiếng Việt để bắt được cả tin nhắn viết không dấu
là thuần lợi.

**Đo được:** `hen gap bac tai cua hang` → khớp luật `time_pressure`. Mọi tin nhắn
**hẹn gặp** đều bị gắn dấu hiệu thúc ép thời gian, rồi luật đó áp sàn confidence
0,58 lên `ap_luc_thoi_gian` ở model.

**Đã đổi:** thay khớp trần `gấp` bằng negative lookahead loại nghĩa "gặp ai / gặp
vấn đề"; siết `khẩn` → `khẩn cấp|khẩn trương`. 14 ca hai nghĩa đều đúng, có test
chặn hồi quy.

**Chỗ đáng nghĩ:** một bước chuẩn hoá tưởng vô hại làm mất thông tin phân biệt
nghĩa, và nó chỉ lộ ra trên loại tin nhắn đời thường phổ biến nhất.

`codebase/ml/tests/test_local_rules.py::test_meeting_up_is_not_read_as_time_pressure`

---

## 3. Golden set 20/20 nhưng bộ probe độc lập chỉ 22/24

**Tin là gì trước đó:** 20/20 và 136/136 biến thể nhiễu nghĩa là model tốt.

**Đo được:** bộ 36 câu soạn **sau đó, độc lập** chỉ đạt recall 22/24 và **3/12
báo nhầm** trên nhóm hợp lệ. Cả 20 case golden đều do nhóm tự soạn khi đã biết
model bắt được gì.

**Chỗ đáng nghĩ:** bộ test do người viết code soạn thì đo lại thứ họ đã biết.
Con số 100% nói về bộ test nhiều hơn nói về model.

`eval/results.md` mục "Phân tích nguyên nhân"

---

## 4. Tin nhắn học phí thật bị chấm `high`

**Đo được:** *"Nhà trường thông báo học phí học kỳ 2 là 3 triệu, phụ huynh nộp
tại phòng kế toán"* → `high` 0,70 kèm `mao_danh_tham_quyen`. Cùng câu đó viết
không dấu chỉ ra `medium` 0,49.

**Chưa sửa.** Sửa đúng cần hiệu chỉnh lại trọng số L4, mà bar đã đóng băng lúc
23:59 N1.

**Chỗ đáng nghĩ:** người dùng là người 60 tuổi. Hét "nhiều dấu hiệu lừa đảo" vào
một tin nhắn thật của trường thì họ không nộp học phí — và lần sau không tin cảnh
báo nữa. Sai hướng này đắt hơn bỏ sót, vì nó phá thứ sản phẩm không xây lại được:
**được tin**.

`codebase/logs/ai-call-trace-20260731T024301Z.jsonl` (hai dòng cuối)

---

## 5. L5 đo trên 1.282 hội thoại thật: recall 0

**Tin là gì trước đó:** so cách gõ của một liên hệ với chính họ trước đó sẽ bắt
được kịch bản chiếm tài khoản.

**Đo được:** recall **0**. Vì **1.132/1.282** hội thoại kẻ gian hỏi tiền ngay sau
**1 tin nhắn**, và **0/1.282** hội thoại có nạn nhân đòi gọi video. Corpus bắt
đầu *sau khi* tài khoản đã bị chiếm — không có phần "trước đó" để so.

**Đã đổi:** khai L5 là **ngoài lát cắt, chưa validate**, thay vì để nó vào chỗ
được chấm mà không có số đo đứng sau.

**Chỗ đáng nghĩ:** dữ liệu có thể không kiểm được ý tưởng, và biết điều đó có giá
trị hơn một con số đẹp không ai kiểm lại.

`eval/results.md` lượt 3 · `codebase/ml/src/chan_ml/evaluate_thread.py`

---

## 6. Corpus 15.840 hội thoại nhưng không nói được tần suất

**Đo được:** mỗi kịch bản gần đúng 427 hội thoại; tỉ lệ "nạn nhân mất tiền" đúng
**33,3% ở mọi nhóm, cả seed lẫn synthetic**; và chỉ **8,1%** câu trong nhóm chiếm
tài khoản là khác nhau.

**Đã đổi:** cột "bao nhiêu người" trong bảng impact §2 **để trống có chủ ý**, kèm
lý do.

**Chỗ đáng nghĩ:** dữ liệu nhiều không đồng nghĩa với bằng chứng. Một corpus cân
bằng nhân tạo trả lời được "trông như thế nào", không trả lời được "phổ biến bao
nhiêu".

`evidence/mining-method.md` mục "Bộ số này KHÔNG chứng minh được cái gì"

---

## 7. Blocklist rỗng, và cái giá của việc lấp nó cho đẹp

**Đo được:** hỏi production 4 prefix khác nhau, `hashes: []` cả bốn. Luồng tra cứu
không thể demo nhánh "đã có báo cáo".

**Đã đổi:** seed 14 chỉ dấu demo từ dải số **không nhà mạng nào cấp** và tên miền
RFC 2606, gắn nhãn `feed_listed`. Màn kết quả nay đọc nguồn: chỉ báo cáo cộng
đồng đã rà soát mới được nói "đã có người báo cáo".

**Chỗ đáng nghĩ:** cách dễ là sinh số ngẫu nhiên và ghi "cộng đồng báo cáo". Số
di động VN sinh ngẫu nhiên gần như chắc chắn trúng số của người thật, và màn hình
sẽ tố cáo họ.

`codebase/intel/src/chan_intel/seed_demo.py`

---

## Cách dùng file này

Chọn **một** mục. Trả lời ba câu bằng lời của mình:

1. Trước đó mình tin điều gì?
2. Số đo nói gì khác đi?
3. Lần sau mình sẽ làm khác chỗ nào?

Đừng chép lại mục này vào reflection — người chấm đọc được cả hai file.
