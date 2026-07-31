# Reflection — Đỗ Hùng Anh

**Vai trò:** Android Developer · **Mã HV:** 2A2026001175

> Rubric chấm riêng phần này: vai trò + phần mình làm + AI hỗ trợ thế nào + **một
> bài học từ case fail của chính nhóm**. Viết bằng lời của bạn, khoảng 300-500
> chữ. Không ai viết hộ được — CP5 bốc ngẫu nhiên một người hỏi về phần có tên
> mình, và câu trả lời phải là của bạn.

---

## Hồ sơ thực tế (tự động từ git — dùng làm dữ kiện, đừng chép lại)

**Git ghi nhận:** 3 commit dưới tên `Lystiger` (dohunganh5002@gmail.com).

**Vùng file đã đụng:**
```
.gitignore
repo/README.md
repo/codebase/README.md
repo/codebase/apps
repo/design/README.md
```

**Commit:**
- `e68c04d5d` Doc: Design and codebase documents
- `0e990114e` Add: FE demo
- `bd69d5143` Add: Design layout for FE


---

## 1. Phần mình làm là gì

*(Cụ thể tới file. "Làm backend" không tính — "viết `X.py`, chịu trách nhiệm
quyết định Y" mới tính.)*

TODO

## 2. AI hỗ trợ thế nào — và chỗ nào mình phải tự quyết

*(Trung thực. Dùng AI nhiều không bị trừ điểm; không giải thích được thì bị.
Nêu ít nhất một chỗ AI đề xuất mà bạn bác bỏ hoặc sửa, và vì sao.)*

TODO

## 3. Một bài học từ case fail của chính nhóm

*(Phải là case fail **thật** của nhóm mình. Vài case có sẵn để chọn — chọn cái
bạn dính trực tiếp, và viết bạn hiểu ra điều gì:)*

- Cửa lọc L1 trả `unknown` tại chỗ mà không bao giờ gọi model, nhưng màn hình
  hiện y như đã chấm xong → tin lừa đảo "pass" âm thầm.
- `"gấp"` và `"gặp"` trùng nhau sau khi bỏ dấu → mọi tin nhắn hẹn gặp bị gắn
  dấu hiệu thúc ép thời gian.
- Tin nhắn học phí thật của nhà trường bị chấm `high` mạo danh.
- L5 đo trên 1.282 hội thoại thật: recall 0, vì corpus không có phần "trước khi
  bị chiếm tài khoản".
- Golden set 20/20 nhưng probe độc lập chỉ 22/24 — bộ case đang đo lại thứ đã biết.

TODO

*(Nguyên liệu: bảy case fail thật có bằng chứng trong [`DECISION-LOG.md`](DECISION-LOG.md) — chọn một mục mình dính trực tiếp, đừng chép lại.)*

## 4. Nếu làm lại, mình làm khác chỗ nào

TODO
