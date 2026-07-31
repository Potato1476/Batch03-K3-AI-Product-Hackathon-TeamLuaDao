# Reflection — Nguyễn Gia Bảo

**Vai trò:** PM · Solution Architect · **Mã HV:** 2A2026019318

> Rubric chấm riêng phần này: vai trò + phần mình làm + AI hỗ trợ thế nào + **một
> bài học từ case fail của chính nhóm**. Viết bằng lời của bạn, khoảng 300-500
> chữ. Không ai viết hộ được — CP5 bốc ngẫu nhiên một người hỏi về phần có tên
> mình, và câu trả lời phải là của bạn.

---

## Hồ sơ thực tế (tự động từ git — dùng làm dữ kiện, đừng chép lại)

**Git ghi nhận:** 28 commit dưới tên `NguyenGiaBao0706` (22025514@vnu.edu.vn).

**Vùng file đã đụng:**
```
.dockerignore
.gitattributes
.gitignore
README.md
eval/README.md
eval/chan-ml-synthetic-v0.4.json
ml/DATASET_CARD.md
ml/MODEL_CARD.md
ml/README.md
ml/pyproject.toml
ml/src/chan_ml
ml/tests/test_continuous.py
ml/tests/test_end_to_end.py
ml/tests/test_policy.py
```

**Commit:**
- `81fd77cf0` Fill spec from real evidence and record what L5 cannot prove yet
- `ea8f398e0` Detect hijacked-account scams across a conversation
- `f2b50cb0e` Fill spec design sections and record honest eval results
- `4cb2c4e02` Ignore local gstack tooling state
- `0ddde24a7` Record rejected candidate golden-set results
- `c646a5aeb` Order Vercel proxy startup before public traffic
- `f3844fbd6` Buffer API requests during Vercel cold starts
- `191e03dc9` Avoid Gateway race during container cold start
- `e1303ea34` Create ephemeral Nginx directories at startup
- `58fab53e1` Route all Vercel traffic through the container
- `5346f7920` Make Vercel container routing production-ready
- `096e527d3` Fix Vercel container runtime logs
- `615c0619d` Use Vercel managed database connection automatically
- `4c3c29942` Deploy complete CHAN stack on Vercel containers
- `39428994f` Train typo-robust phishing model with audited labels
- `40452ec71` Harden team dataset training and phishing detection
- `56745c5d7` Retrain phishing model for fake shipper scenario
- `615e41f39` Detect soft fake-shipper payment scams
- `b92efc5b3` Document secure context requirement for voice input
- `d1566f67f` Add OCR and private voice input to web app
- `d3fd87e77` Connect web client to phishing detection backend
- `565f90bea` feat: publish ML artifacts and detection API
- `40c4eb2b4` Expand phishing coverage to 36 scenario families
- `ec6731b9a` Add privacy-preserving threat intel service
- `300bf97dd` Consolidate CHAN project under repo folder
- `e1c16caa5` Add continuous phishing training platform
- `6f92e2ac3` Link shared ML engine from product scaffold
- `59b3880c5` Add CHAN phishing detection ML pipeline


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
