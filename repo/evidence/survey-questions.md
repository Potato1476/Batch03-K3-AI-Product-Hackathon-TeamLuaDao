# Bộ câu hỏi khảo sát — chuẩn A

**Mục tiêu:** ≥20 người ngoài nhóm · ≥50% xác nhận pain · log đủ câu hỏi và
**từng câu trả lời nguyên văn** (không tóm tắt). Không có log thì không tính.

**Ai hỏi được:** cả lớp là người dùng thật của bài toán này (ai cũng có người
thân lớn tuổi). Hỏi trong giờ nghỉ, mỗi người 3-4 phút.

**Luật hỏi (guide §1.3):** hỏi về **lần gần nhất đã xảy ra**, không hỏi ý kiến về
tính năng. "Bạn có muốn có app cảnh báo lừa đảo không?" → ai cũng gật, dữ liệu
thu được vô dụng.

---

## Câu sàng lọc

**S.** *"Trong 3 tháng gần đây, bạn hoặc người nhà bạn có nhận tin nhắn nào nghi
là lừa đảo không?"*
→ Không: ghi lại rồi dừng, vẫn tính vào mẫu (mẫu số n).
→ Có: hỏi tiếp.

## Ba câu chính — hỏi đúng thứ tự, ghi nguyên văn

**Q1 — Chuyện gì đã xảy ra?**
> *"Kể lần gần nhất đi. Tin nhắn đó nói gì, đến từ đâu, và lúc đó bạn/người nhà
> đã làm gì?"*

Cần moi ra: ai nhận · nội dung · làm gì tiếp (bấm link / chuyển tiền / hỏi ai /
bỏ qua).

**Q2 — Lúc đó đã kiểm tra bằng cách nào, và nó hỏng ở đâu?**
> *"Lúc phân vân, bạn/người nhà làm gì để biết thật hay giả? Mất bao lâu? Có
> chắc chắn được không?"*

Cần moi ra: cách đang dùng hôm nay (gọi con cháu · tự tra Google · hỏi ngân hàng
· đoán) và **nó fail ở đâu** — đây là phần quan trọng nhất, không được bỏ.

**Q3 — Hậu quả.**
> *"Kết cục thế nào? Có ai mất tiền, mất thời gian, hay lo lắng mất mấy hôm
> không?"*

Cần moi ra: con số nếu có (bao nhiêu tiền, bao nhiêu phút, mấy lần một tháng).

## Câu chốt willing user

**W.** *"Bọn mình đang làm thử một công cụ cho việc này. Mai bạn thử 5 phút rồi
nói thật là dở chỗ nào được không?"*
→ Có: **xin tên + cách liên lạc**, ghi vào bảng willing user trong `spec.md` §8.
Cần ≥3 người (tiêu chí nghiệm thu #5), và ≥2 trong số đó phải quay lại ở vòng
validation CP5 (R6).

---

## Cách tính "xác nhận pain"

Chốt trước khi đi hỏi, để lúc đếm không tự nới:

> Một người **xác nhận** khi trả lời Q1 có một tình huống cụ thể đã xảy ra
> **và** Q2 cho thấy cách kiểm tra hiện tại của họ mất >5 phút, phải phiền người
> khác, hoặc không kết luận được.
>
> Chỉ "thấy phiền" mà không kể được lần cụ thể → **không** tính là xác nhận.

Ngưỡng đạt: **≥50% số người được hỏi**.

## Chia người đi hỏi

| Người hỏi | Chỉ tiêu | Đã hỏi |
|---|---|---|
| Nguyễn Gia Bảo | 4 | ☐ |
| Nguyễn Lê Minh | 4 | ☐ |
| Nguyễn Thị Lý | 4 | ☐ |
| Hùng Anh | 4 | ☐ |
| Tuấn Anh | 4 | ☐ |

Ghi thẳng vào [`survey-responses.md`](survey-responses.md) ngay lúc hỏi — chép
lại sau là mất nguyên văn.
