# Dataset card — CHAN-Dataset

**Người chuẩn bị dataset:** Nguyễn Tuấn Anh (2A2026001669)

Corpus hội thoại lừa đảo tiếng Việt do nhóm lắp ráp, là vật liệu cho §1-§2 của
[`../../spec.md`](../../spec.md) và cho bộ đo trong [`../../eval/`](../../eval/).

## Vì sao dữ liệu thô không nằm trong repo

`CHAN-Dataset/` nặng **481 MB / 15.840 file JSON** nên nằm trong `.gitignore`.
Thư mục này giữ lại phần **kiểm chứng được mà vẫn nhẹ** — 96 KB:

| Có trong repo | Nội dung |
|---|---|
| `DATASET-README.md` | Mô tả bộ dữ liệu do người lắp viết |
| `00_Documentation/taxonomy.md` | Cây kịch bản lừa đảo |
| `00_Documentation/annotation_guideline.md` | Quy tắc gán nhãn — thứ quyết định số đếm có kiểm lại được hay không |
| `00_Documentation/label_definition.json` | Định nghĩa từng nhãn |
| `00_Documentation/version.md` | Phiên bản bộ dữ liệu |
| `metadata/sources.json` | **6 nguồn seed công khai** có tên |
| `metadata/scenario_tree.json`, `signal_tree.json`, `emotion_tree.json`, `languages.json` | Cấu trúc phân loại |
| `samples/` | 3 hội thoại đầy đủ, mỗi loại một mẫu |

## Ba mẫu trong `samples/`

| File | Loại | Nguồn |
|---|---|---|
| `conv_social_hacked_fb_094.json` | Chiếm tài khoản Facebook — 15 tin, đủ 5 giai đoạn | `seed_chongluadao` |
| `conv_authority_police_001.json` | Mạo danh công an | seed |
| `conv_neg_bank_001.json` | **Hội thoại ngân hàng hợp lệ** — nhóm negative | — |

Ba file này đủ để người chấm thấy **cấu trúc bản ghi**: `source`, `source_type`,
`scenario`, `outcome`, và từng tin nhắn có `sender`, `stage`, `signals`, `risk`.
Đó là các trường mà script đếm trong
[`../scripts/mine_chan_dataset.py`](../scripts/mine_chan_dataset.py) đọc.

## Số đếm trên toàn bộ corpus

Đã chạy và ghi lại trong [`../mining-results.json`](../mining-results.json) và
[`../mining-results.md`](../mining-results.md):

- 15.840 hội thoại · 181.943 tin nhắn · trung vị 11 tin/hội thoại
- 6.391 hội thoại từ 6 nguồn seed công khai · 7.220 synthetic · 2.229 hợp lệ
- 1.282 hội thoại thuộc kịch bản chiếm tài khoản người quen

## Ba giới hạn đã đo được của chính bộ này

Ghi ở đây thay vì để người chấm tự phát hiện:

1. **Cân bằng nhân tạo** — mỗi kịch bản gần đúng 427 hội thoại; tỉ lệ "mất tiền"
   đúng 33,3% ở mọi nhóm và cả hai loại nguồn. ⇒ không dùng để nói tần suất.
2. **Lặp câu nặng** — 8.288 tin của kẻ gian trong nhóm chiếm tài khoản chỉ gồm
   **675 câu khác nhau (8,1%)**.
3. **Nhãn bị dán chéo** — câu lặp nhiều nhất trong nhóm *chiếm tài khoản người
   quen* lại là lời mạo danh cơ quan chức năng.

Chi tiết: [`../mining-method.md`](../mining-method.md).

## Lấy bản đầy đủ

Dữ liệu thô nằm ngoài repo. Người chấm cần bản đầy đủ để chạy lại script đếm thì
liên hệ Nguyễn Tuấn Anh.
