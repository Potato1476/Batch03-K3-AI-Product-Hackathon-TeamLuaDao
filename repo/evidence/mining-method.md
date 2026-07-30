# Phương pháp đếm — chuẩn B

> Rubric R1 yêu cầu phương pháp đếm **kiểm lại được**: đếm trên tập nào, tiêu chí
> gán nhãn là gì, ai gán, script đâu. File này trả lời đúng bốn câu đó, và nói rõ
> luôn những gì bộ số **không** chứng minh được.

## Đếm trên tập nào

`repo/CHAN-Dataset/` — corpus hội thoại lừa đảo tiếng Việt do nhóm lắp ráp trong
sự kiện. Quy mô đếm được bằng script:

- **15.840 hội thoại**, **181.943 tin nhắn**, trung vị 11 tin mỗi hội thoại.
- Nguồn (`source` trong từng file):

  | Nguồn | Loại | Số hội thoại |
  |---|---|---|
  | `synthetic_llm` | LLM tự sinh | 7.220 |
  | `seed_phishvn` | PhishVN Dataset — Mendeley Data | 1.710 |
  | `seed_chongluadao` | ChongLuaDao.vn Anti-Scam Database | 1.704 |
  | `seed_sms_spam` | Vietnamese SMS Spam — VNCERT & GitHub | 1.702 |
  | `seed_conscambench` | ConScamBench-278 | 427 |
  | `seed_scc` | Scam Conversation Corpus — Zenodo | 425 |
  | `seed_emscad` | Employment Scam Aegean Dataset | 423 |
  | *(không có `source_type`)* | hội thoại hợp lệ, thư mục `02_Negative` | 2.229 |

## Tiêu chí gán nhãn

Nhãn có sẵn trong từng file JSON, không do người đọc gán lại:

- một hội thoại = một file `conv_*.json` có khoá `messages`;
- `source_type ∈ {seed, synthetic}` → hội thoại lừa đảo; thiếu khoá này → hội
  thoại hợp lệ trong `02_Negative`;
- kịch bản chiếm tài khoản người quen = `scenario ∈ {Hacked_FB, Hacked_Zalo,
  Relative_Borrow}`;
- "có lời hỏi tiền" = tồn tại tin của `sender = scammer` chứa một trong
  `chuyen / chuyển / tien / tiền / stk / tài khoản`.

## Ai gán, script đâu

Nhãn do người lắp corpus gán khi sinh dữ liệu (`00_Documentation/annotation_guideline.md`).
Script đếm: [`scripts/mine_chan_dataset.py`](scripts/mine_chan_dataset.py).

```bash
.venv/bin/python evidence/scripts/mine_chan_dataset.py \
  --dataset CHAN-Dataset --output evidence/mining-results.json
```

Không có bước thủ công nào giữa chừng. Người ngoài nhóm chạy lại phải ra đúng số
trong [`mining-results.json`](mining-results.json).

## ⚠️ Bộ số này KHÔNG chứng minh được cái gì

Đây là phần quan trọng nhất của file, và nó nằm ở đây thay vì bị giấu đi.

**Corpus được cân bằng nhân tạo, không phải mẫu của thực tế.** Hai dấu hiệu đếm
được:

1. Mỗi kịch bản có gần đúng cùng số hội thoại: Hacked_FB 427, Hacked_Zalo 428,
   Stock 427, Tax 427, Court 427, Sugar 427, Deepfake 427, Refund 427… Tần suất
   thật ngoài đời không bao giờ đều như vậy.
2. Trường `outcome` chia gần đúng ba phần bằng nhau — `victim_transferred_money`
   4.539, `victim_suspicious_refused` 4.539, `victim_detected_and_blocked` 4.533
   — và tỉ lệ "mất tiền" là **33,3% ở mọi nhóm kịch bản và ở cả nguồn seed lẫn
   synthetic**. Con số đều đến mức đó là do cách sinh dữ liệu, không phải do quan
   sát.

Vì vậy **không được dùng corpus này để nói "kịch bản X phổ biến nhất" hay "33%
nạn nhân mất tiền"**. Đó sẽ là số bịa mang hình dạng số thật, đúng loại sai phạm
rubric loại thẳng.

**Corpus chứng minh được:** các mẫu tin nhắn lừa đảo này tồn tại và trông như thế
nào (có nguồn public dẫn được), đủ để làm vật liệu kiểm thử — xem `eval/`.

**Vẫn còn thiếu để đạt R1:** bằng chứng **chuẩn A** — khảo sát ≥20 người ngoài
nhóm về *lần gần nhất* họ hoặc người nhà nhận tin nhắn lừa đảo, ≥50% xác nhận,
log đủ câu hỏi và từng câu trả lời nguyên văn. Bộ câu hỏi đã soạn sẵn trong
[`survey-questions.md`](survey-questions.md); chỉ còn thiếu người đi hỏi.
