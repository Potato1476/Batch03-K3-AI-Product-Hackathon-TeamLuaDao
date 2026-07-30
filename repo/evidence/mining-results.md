# Kết quả mining — CHAN-Dataset

Phương pháp và giới hạn: [`mining-method.md`](mining-method.md).
Số máy sinh: [`mining-results.json`](mining-results.json).
Chạy lại: `.venv/bin/python evidence/scripts/mine_chan_dataset.py --dataset CHAN-Dataset --output evidence/mining-results.json`

## Quy mô

| Chỉ số | Giá trị |
|---|---|
| Hội thoại | **15.840** |
| Tin nhắn | **181.943** |
| Trung vị tin/hội thoại | 11 |
| Hội thoại lừa đảo | 13.611 (seed 6.391 · synthetic 7.220) |
| Hội thoại hợp lệ (`02_Negative`) | 2.229 |
| Kịch bản chiếm tài khoản người quen | 1.282 (Hacked_FB 427 · Hacked_Zalo 428 · Relative_Borrow 427) |
| Trong đó từ nguồn seed công khai | 1.282 |

Sáu nguồn seed công khai có tên: PhishVN (Mendeley) · ChongLuaDao.vn · Vietnamese
SMS Spam (VNCERT) · ConScamBench-278 · Scam Conversation Corpus (Zenodo) ·
EMSCAD.

## Năm ví dụ nguyên văn — kịch bản chiếm tài khoản người quen

Mọi câu dưới đây mở lại được bằng đường dẫn kèm theo.

| # | Nguyên văn | Nguồn |
|---|---|---|
| 1 | "App ngân hàng của mình bị khóa chuyển tiền do nhập sai OTP, mà mình đang cần thanh toán hóa đơn ngay." | `01_Scenarios/Social/Hacked_FB/conversations/conv_social_hacked_fb_001.json` · seed_chongluadao |
| 2 | "Tài khoản ngân hàng của mình đang bị lỗi bảo trì đột xuất, mà mình cần chuyển tiền thanh toán tiền hàng gấp cho khách." | `…/conv_social_hacked_fb_002.json` · seed_chongluadao |
| 3 | "Bạn chuyển giùm mình qua số tài khoản đối tác này, tối khoảng 8h xong việc mình gửi lại bạn." | `…/conv_social_hacked_fb_094.json` · seed_chongluadao |
| 4 | "Hi bạn! Bạn có đang rảnh không, cho mình nhờ tí việc quan trọng này!" | `…/conv_social_hacked_fb_094.json` · seed_chongluadao |
| 5 | "Nếu không xử lý trực tuyến ngay bây giờ thì hệ thống sẽ khóa hồ sơ!" | lặp 244 lần trong nhóm chiếm tài khoản — xem mục chất lượng dưới |

## Ba vấn đề chất lượng của chính corpus này

Đếm được, và ảnh hưởng trực tiếp tới việc dùng nó làm bằng chứng:

**1. Corpus cân bằng nhân tạo.** Mỗi kịch bản gần đúng 427 hội thoại. Trường
`outcome` chia đúng ba phần bằng nhau, nên tỉ lệ "nạn nhân mất tiền" là **33,3%
ở mọi nhóm kịch bản, ở cả nguồn seed lẫn synthetic**. Con số đều đến vậy là do
cách sinh dữ liệu. ⇒ **Không dùng corpus để nói kịch bản nào phổ biến hơn hay
thiệt hại bao nhiêu.**

**2. Lặp câu rất nặng.** 8.288 tin nhắn của kẻ gian trong nhóm chiếm tài khoản
chỉ gồm **675 câu khác nhau — 8,1%**. Năm câu lặp nhiều nhất xuất hiện 215-244
lần mỗi câu. ⇒ Model học trên đây dễ thuộc lòng template thay vì hiểu kịch bản;
đây là một lời giải thích khả dĩ cho việc model bắt rất tốt câu quen và trượt
câu lạ (xem `eval/results.md`).

**3. Nội dung bị dán chéo kịch bản.** Câu lặp nhiều nhất trong nhóm *chiếm tài
khoản người quen* lại là lời mạo danh cơ quan chức năng: *"Anh/chị sẽ phải chịu
trách nhiệm trước pháp luật nếu cố tình chống đối!"* (229 lần), *"Hệ thống đang
đối soát dữ liệu, anh/chị giữ máy…"* (218 lần). Một người bạn bị hack không nói
như vậy. ⇒ Nhãn kịch bản của corpus không đáng tin ở mức từng hội thoại.

## Corpus này chứng minh và không chứng minh cái gì

**Chứng minh được:** các mẫu tin nhắn lừa đảo tồn tại, trông như thế nào, và có
nguồn public dẫn lại được. Đủ làm vật liệu kiểm thử.

**Không chứng minh được:** ai đau, đau bao nhiêu, bao lâu một lần. Corpus không
phải mẫu của dân số.

⇒ **R1 vẫn chưa đủ.** Cần bằng chứng **chuẩn A**: khảo sát ≥20 người ngoài nhóm,
≥50% xác nhận, log đủ câu hỏi + từng câu trả lời nguyên văn. Bộ câu hỏi sẵn ở
[`survey-questions.md`](survey-questions.md), ô log sẵn ở
[`survey-responses.md`](survey-responses.md). Còn thiếu đúng một thứ: người đi hỏi.
