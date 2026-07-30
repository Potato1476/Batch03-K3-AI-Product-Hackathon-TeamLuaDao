# AI SPEC — [Tên lát cắt] · Nhóm [XX] · Zone [X]

Hướng: [ ] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [ ] Tính năng mới

> Hạn cứng: commit trước 23:59 ngày 1. Quality bar (§7) chốt từ thời điểm nộp, không sửa sau đó.
> Hướng dẫn viết từng mục: `../02-guide.md`. Rubric: `../04-rubric.md`.

## §1. User & Job

- **Job executor + workflow** (đính kèm worksheet JTBD / ảnh sơ đồ): TODO
- **Core JTBD** (không tên sản phẩm/AI trong câu): TODO
- **Problem statement** (KHÔNG chữ AI): TODO
- **Evidence** — chuẩn A (khảo sát ≥20 người ngoài nhóm, ≥50% xác nhận) và/hoặc chuẩn B (số mining đếm được + phương pháp đếm kiểm lại được). Log đầy đủ trong repo:
  - Số liệu mining / kết quả khảo sát (n = ?, % xác nhận): TODO
  - Phương pháp đếm (ai đếm, đếm trên tập nào, tiêu chí gán nhãn): TODO
  - Log đầy đủ: `evidence/` hoặc link file TODO

  **≥5 quote/ví dụ nguyên văn + nguồn:**

  | # | Quote nguyên văn | Nguồn (file/dòng hoặc người + vai) |
  |---|---|---|
  | 1 | | |
  | 2 | | |
  | 3 | | |
  | 4 | | |
  | 5 | | |

## §2. Impact & quyết định chọn

**Bảng impact ≥3 ứng viên:**

| Ứng viên | Bao nhiêu người | Tần suất | Tốn gì mỗi lần | Khả thi trong 1,5 ngày | Chọn/Loại |
|---|---|---|---|---|---|
| A | | | | | |
| B | | | | | |
| C | | | | | |

- **Ứng viên ĐÃ LOẠI + vì sao** (giữ lại, không xoá): TODO
- **Ứng viên CHỌN + vì sao (bằng số)**: TODO

## §3. Giải pháp tương tự đã nghiên cứu

| Sản phẩm | Flow của họ | Đáng học | Đáng né | Mình khác gì |
|---|---|---|---|---|
| [Sản phẩm 1] | | | | |
| [Sản phẩm 2] | | | | |

## §4. Thiết kế

- **Lát cắt MỘT CÂU** (1 user · 1 việc · 1 quyết định AI · 1 kết quả): TODO
- **Non-goals (≥3 thứ KHÔNG build):**
  1. TODO
  2. TODO
  3. TODO
- **Mức prototype nhắm tới:** [ ] Sketch [ ] Mock [ ] Working
  - Phần THẬT: TODO
  - Phần MOCK: TODO *(phải khớp với ghi chú trong `codebase/README.md`)*
- **Automation:** [ ] augment [ ] conditional [ ] automate
  - Lý do theo cost-of-error (sai thì ai chịu hậu quả gì, hồi phục được không): TODO

### §4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR)

| Nguyên tắc | Áp cụ thể vào đâu trong prototype (file/màn hình) |
|---|---|
| | |
| | |
| | |
| | |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

**4 lớp chỗ khó:**

| Lớp | Tên lớp | Cụ thể hoá trong bài của nhóm |
|---|---|---|
| ① | Không có căn cứ / model không biết | |
| ② | Mơ hồ, độ tin thấp | |
| ③ | Đòi hỏi ngoài phạm vi | |
| ④ | Case đặc thù domain | |

**Kịch bản (≥8, phủ đủ 4 lớp):**

| # | Lớp | Input / tình huống | Hành vi mong muốn của hệ thống |
|---|---|---|---|
| 1 | ① | | |
| 2 | ① | | |
| 3 | ② | | |
| 4 | ② | | |
| 5 | ③ | | |
| 6 | ③ | | |
| 7 | ④ | | |
| 8 | ④ | | |

## §6. Bốn đường đi của trải nghiệm

| Đường đi | Hệ thống làm gì | Thể hiện ở đâu trong prototype |
|---|---|---|
| Happy path | | |
| Low-confidence (②) | | |
| Failure / không căn cứ (①) | | |
| Correction (user sửa) | | |
| Bị đòi ngoài phạm vi (③) | | |
| Case đặc thù domain (④) | | |

## §7. Kiểm thử

**Chiều chất lượng + định nghĩa kiểm chứng được** (người ngoài nhóm chấm phải ra cùng kết quả):

| Chiều chất lượng | Định nghĩa PASS (kiểm chứng được) | Cách chấm |
|---|---|---|
| | | |
| | | |

- **Golden set:** ≥20 case — ≥2 case/lớp chỗ khó + 8-10 case thường + 2-4 case hiếm; ≥10 case từ chatlog thật. File: [`eval/golden-set.md`](eval/golden-set.md)
- **Quality bar** *(chốt từ 23:59 N1, giữ nguyên sau đó)*: "Đạt khi ≥ ___% qua bộ, và ___"
- **Kết quả các lượt chạy:** bảng đầy đủ trong [`eval/results.md`](eval/results.md)

| Lượt | Thời điểm | Thay đổi gì so với lượt trước | % pass | Đối chiếu bar |
|---|---|---|---|---|
| 1 | | | | |

## §8. Phân công & kế hoạch

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

| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| | | |
