# Golden set

**Tổng số case:** 20/20 tối thiểu
**Từ chatlog thật (`data/vlearn-pack/`):** **0**/10 tối thiểu — xem "Ghi chú trung thực về nguồn" bên dưới
**Người xây:** Team LuaDao QA (`CHẮN_System_TestCases_v1.2.xlsx`, sheet `Golden Set (20 Cases)`, lập 2026-07-30)
**Người review chéo:** TODO — cần tên người thứ hai đã chấm độc lập (guide §2.6 bước 4)

Bộ case gốc do nhóm tự xây trong workbook Excel. File này là bản chép lại vào repo
để chấm được; bản chạy máy đầy đủ nằm ở
[`rules-rb-20260730-5-golden-results.json`](rules-rb-20260730-5-golden-results.json).

## Cơ cấu

| Loại | Yêu cầu | Hiện có | Đạt |
|---|---|---|---|
| Lớp ① không có căn cứ | ≥2 | 2 (G09, G10) | ✅ |
| Lớp ② mơ hồ / low-confidence | ≥2 | 2 (G11, G12) | ✅ |
| Lớp ③ ngoài phạm vi | ≥2 | 2 (G13, G14) | ✅ |
| Lớp ④ đặc thù domain | ≥2 | 2 (G15, G16) | ✅ |
| Case thường | 8-10 | 8 (G01-G08) | ✅ |
| Case hiếm | 2-4 | 4 (G17-G20) | ✅ |
| Case từ chatlog thật | ≥10 | **0** | ❌ |

## Ghi chú trung thực về nguồn

Cột "Nguồn Dữ liệu" trong workbook ghi 10 case là "Chatlog thật" và G01 trỏ về
`data/vlearn-pack/...`. **Nhãn này không kiểm chứng được.** Chatlog VLearn được
cấp là hội thoại học viên × AI tutor về nội dung học; tìm toàn bộ 11.383 dòng
không có một dòng nào chứa "lừa đảo", "OTP", "chuyển tiền", "mạo danh" hay
"trúng thưởng":

```
grep -icE "lừa đảo|lua dao|OTP|chuyển tiền|scam|mạo danh|trúng thưởng" \
  data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv
0
```

Vì vậy bảng dưới ghi nguồn thật: **toàn bộ 20 case do nhóm tự soạn**, dựa trên
mẫu tin nhắn lừa đảo phổ biến tại Việt Nam. Rubric R4 cho 4 điểm mục golden set
yêu cầu ≥10 case từ chatlog thật — mục này **chưa đạt**, và ghi nhận đúng như
vậy thay vì giữ nhãn nguồn không kiểm lại được (rubric: "số liệu bị chỉnh sửa
hoặc che giấu sẽ không được tính").

## Chiều chất lượng & định nghĩa PASS

*(Đồng bộ với `spec.md` §7.)*

| Chiều | Định nghĩa PASS (người ngoài nhóm chấm phải ra cùng kết quả) |
|---|---|
| **C1 · Mức rủi ro đúng** | `risk` trả về khớp mức kỳ vọng ghi ở cột "Kỳ vọng". Khi kỳ vọng ghi khoảng điểm thì `score` phải nằm trong khoảng đó. Chấm bằng máy, không cần diễn giải. |
| **C2 · Dấu hiệu đúng** | Mọi signal code liệt kê ở cột kỳ vọng đều có mặt trong `signals` trả về. Signal thừa không tính fail (bộ 8 dấu hiệu là đa nhãn). |
| **C3 · Không trấn an sai** | Output không bao giờ chứa nhãn "an toàn"/"safe"/"ok"/"clean". `risk` chỉ nhận `high`/`medium`/`unknown`. Kiểm bằng test tự động `forbidden_labels` trong rule bundle. |
| **C4 · OTP không rời máy** | Với case chứa/đòi mã OTP, verdict phải sinh ở L1 trên thiết bị (`engine_version = l1-local`) và không có request nào tới `/v1/analyze`. |
| **C5 · Bền với nhiễu chính tả** | Case được sinh biến thể tự động (thiếu dấu, sai 1 ký tự, chèn dấu phân tách, đổi khoảng trắng) phải giữ nguyên mức rủi ro của case gốc. |

## Danh sách case

Nguồn của toàn bộ 20 case: **nhóm tự soạn** theo mẫu tin nhắn lừa đảo phổ biến ở VN.

| ID | Loại | Input (rút gọn) | Expected behavior (PASS khi...) |
|---|---|---|---|
| G01 | thường | "…em là cán bộ thuế quận 1. Hồ sơ thuế của anh có lỗi, cập nhật ngay trong 2h…" | `high`, score ≥ 0.70 · signals ⊇ `mao_danh_tham_quyen`, `ap_luc_thoi_gian` |
| G02 | thường | "Vietcombank thông báo: tài khoản bị khoá. Đăng nhập http://vcb-sec.com để mở lại." | `high` · signals ⊇ `mao_danh_tham_quyen` |
| G03 | thường | "Chuyển ngay 5 triệu vào STK 123456789… chuyển xong xoá tin nhắn, không nói với gia đình." | `high` · signals ⊇ `yeu_cau_bi_mat`, `tk_ca_nhan` |
| G04 | thường | "Mã OTP xác thực giao dịch VCB của bạn là 839201…" | `high`, chặn tại L1 · signals ⊇ `yeu_cau_otp` |
| G05 | thường | "Thông báo từ Cục Cảnh sát: bạn có giấy phạt nguội 5 triệu. Truy cập http://phatnguoi-gov.com…" | `high` · signals ⊇ `mao_danh_tham_quyen` |
| G06 | thường | "Thuê bao SIM chưa chuẩn hoá. Sẽ khoá SIM sau 24h…" | `high` · signals ⊇ `ap_luc_thoi_gian` |
| G07 | thường | "Chúc mừng quý khách trúng thưởng xe SH và 100 triệu. Truy cập http://trungthuong2026.com…" | `high` · signals ⊇ `loi_ich_bat_thuong` |
| G08 | thường | "Anh vào link gock-app.apk để tải phần mềm hỗ trợ khai thuế và bật quyền trợ năng." | `high` · signals ⊇ `cai_app_ngoai` |
| G09 | ① | "Alo / 123456 / ???" | `unknown`, score < 0.35, `signals = []` — không đủ căn cứ thì không bịa dấu hiệu |
| G10 | ① | "Chúc anh một ngày tốt lành, khi nào rảnh qua em chơi." | `unknown`, score < 0.10, `signals = []` |
| G11 | ② | "Cô ơi cháu là Tuấn đây, điện thoại cháu bị hỏng nên dùng số này. Cô đang rảnh không?" | `medium`, score ∈ [0.35, 0.69] — nghi mạo danh người quen nhưng chưa đủ chắc để báo `high` |
| G12 | ② | "Tuyển cộng tác viên xem Youtube 500k/ngày. Nhắn hộp thư Zalo 0988776655…" | `medium` · signals ⊇ `loi_ich_bat_thuong`, `chuyen_kenh` |
| G13 | ③ | "Tôi vừa bị lừa mất 20 triệu qua Zalo, bây giờ làm sao để đòi lại tiền từ ngân hàng?" | Ngoài phạm vi: không hứa đòi được tiền, hướng dẫn liên hệ Công an/Ngân hàng |
| G14 | ③ | "Có nên đầu tư vào sàn giao dịch coin ABC này không, cam kết lãi 30%/tháng?" | Ngoài phạm vi: không tư vấn đầu tư, cảnh báo mô hình cam kết lãi cao |
| G15 | ④ | "Vietcombank: Số dư TK 0011001234567 +1,000,000 VND… Ref: Luong T7." | `unknown`, score < 0.20 — **không được báo động nhầm** SMS biến động số dư thật |
| G16 | ④ | "Công an TP Hà Nội cảnh báo: hiện có thủ đoạn mạo danh công an. Bà con tuyệt đối KHÔNG chuyển tiền." | `unknown`, score < 0.35 — hiểu ngữ cảnh bảo vệ, không đọc ngược thành mạo danh |
| G17 | hiếm | "C.h.a.o a.n.h, e.m l.a c.a.n b.o t.h.u.e…" | Sau chuẩn hoá L0 → `high` · signals ⊇ `mao_danh_tham_quyen` |
| G18 | hiếm | "Chúc mừng bạn nhận quà 50Tr. Z.a.l.o: O.9.0.9.1.2.3.4.5.6" | Sau chuẩn hoá L0 → `medium` hoặc `high` |
| G19 | hiếm | "Nhấp vào bit.ly/3xYz12 để cập nhật tài khoản VCB gấp trước 17h." | Tách được URL rút gọn → `high` |
| G20 | hiếm | "Gửi mã OTP 6 số vừa nhận để hỗ trợ huỷ lệnh chuyển tiền nhầm 50 triệu." | `high`, chặn tại L1 · signals ⊇ `yeu_cau_otp` |

## Bộ biến thể nhiễu (chạy kèm, không thay golden set)

Mỗi case gốc được sinh 8 biến thể xác định (seed `20260731`): thiếu dấu, xoá 1 ký
tự, đảo 2 ký tự liền, thay ký tự cạnh trên bàn phím, chèn dấu phân tách, đổi
khoảng trắng. Tổng 136 biến thể. Dùng để đo chiều C5; không tính vào 20 case.

## Cách chạy lại

```bash
.venv/bin/chan-evaluate-workbook \
  --model codebase/ml/artifacts/chan-signal-model.joblib \
  --workbook '<đường dẫn>/CHẮN_System_TestCases_v1.2.xlsx' \
  --rules codebase/rules/bundle.json \
  --typo-variants 8 --typo-seed 20260731 \
  --output eval/<run-id>-golden-results.json
```
