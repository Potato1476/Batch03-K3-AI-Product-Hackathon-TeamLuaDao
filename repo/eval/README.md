# eval/ — Golden set & kết quả đo

Chấm theo rubric R4 (15 điểm) và checklist CP3.

| File | Nội dung |
|---|---|
| [golden-set.md](golden-set.md) | ≥20 case + expected behavior |
| [results.md](results.md) | Bảng kết quả từng lượt chạy, đủ mọi case |
| `runs/` | Output thô của từng lượt (raw log) |

## Cơ cấu golden set bắt buộc (R4, 4 điểm)

- ≥2 case cho **mỗi** lớp chỗ khó ①②③④ → ≥8 case
- 8-10 case **thường**
- 2-4 case **hiếm**
- ≥10 case lấy từ **chatlog thật** (`../../data/`)

## Nguyên tắc ghi kết quả

Ghi **đủ mọi case, kể cả case fail**. Kết quả thấp vẫn được tính đủ điểm nếu ghi nhận trung thực; số liệu bị chỉnh sửa hoặc che giấu thì không được tính.
