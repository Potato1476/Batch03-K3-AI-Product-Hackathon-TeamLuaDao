# Reflection — Nguyễn Lê Minh

**Vai trò:** Web Developer

> Rubric chấm riêng phần này: vai trò + phần mình làm + AI hỗ trợ thế nào + **một
> bài học từ case fail của chính nhóm**. Viết bằng lời của bạn, khoảng 300-500
> chữ. Không ai viết hộ được — CP5 bốc ngẫu nhiên một người hỏi về phần có tên
> mình, và câu trả lời phải là của bạn.

---

## Hồ sơ thực tế (tự động từ git — dùng làm dữ kiện, đừng chép lại)

**Git ghi nhận:** 10 commit dưới tên `g9-9g` (leminhnguyen1924@gmail.com / leminhnguyen1925@gmail.com).

**Vùng file đã đụng:**
```
repo/README.md
repo/codebase/README.md
repo/codebase/TEAM_HANDOFF.md
repo/codebase/api
repo/codebase/apps
repo/codebase/demo-backup
repo/codebase/detection
repo/codebase/docker-compose.yml
repo/codebase/gateway
repo/codebase/intel
repo/codebase/logs
repo/codebase/ml
repo/codebase/prompts
repo/codebase/rules
```

**Commit:**
- `0e67b5e5e` Merge pull request #3 from Potato1476/fix/vietnamese-on-device-speech
- `f9839601d` Fix Vietnamese speech input and show recording state honestly
- `ce90c9930` Document APIs and add Intel PostgreSQL tests
- `366193e92` Fix gateway port and Intel prefix handling
- `62db9f7ae` Refactor gateway to delegate internal services
- `227617f13` Merge pull request #2 from Potato1476/feature/implement-backend
- `18fd098e4` Merge branch 'main' of https://github.com/Potato1476/Batch03-K3-AI-Product-Hackathon-TeamLuaDao into feature/implement-backend
- `fac7cb886` Implement Backend modules
- `c916f9a9a` Merge pull request #1 from Potato1476/add-repo-scaffold
- `dc78c362d` Add repo/ submission scaffold for teams


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

## 4. Nếu làm lại, mình làm khác chỗ nào

TODO
