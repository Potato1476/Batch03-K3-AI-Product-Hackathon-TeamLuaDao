# CHAN — Giao kèo thiết kế (layout & theme)

> Nguồn sự thật duy nhất về **màu, chữ, khoảng cách, component và layout** của CHẮN.
> Trích xuất từ prototype Claude Design `CHAN.dc.html` · phiên bản 1.1 · 2026-07-30
> Song hành với [`docs/CHAN-ARCHITECTURE.md`](../docs/CHAN-ARCHITECTURE.md) (kiến trúc & bất biến bảo mật).

**Cách dùng file này:** trước khi viết dòng UI đầu tiên, cả nhóm đọc §1 → §4 và ký vào §14. Sau đó mọi PR chạm giao diện phải qua checklist §13. Nếu bạn cần một giá trị màu/kích thước không có trong file này — đừng tự chế, mở issue và bổ sung vào đây trước.

---

## 0. Chốt tên thương hiệu

Repo đang dùng lẫn lộn hai cách viết. Chốt như sau:

| Ngữ cảnh | Viết là | Ví dụ |
|---|---|---|
| Logo, wordmark trong app, tên file, domain | `CHAN` | ảnh `logo-full.png`, chữ 24px trên Trang chủ, `chan.vn` |
| Mọi câu văn tiếng Việt (doc, slide, copy trong app) | `CHẮN` | "CHẮN không nhìn thấy số bác nhập" |

Lý do: logotype không dấu để đọc được ở cả hai thị trường và không vỡ khi render font thiếu dấu; văn bản có dấu vì đó mới là nghĩa thật ("chắn" = chặn lại).

**Tài sản thương hiệu**

| File | Dùng ở đâu | Kích thước cố định |
|---|---|---|
| `logo-full.png` | Sidebar giới thiệu, landing, slide | rộng 150px, cao tự động |
| `logo-mark.png` | Header Trang chủ (46×46), toast (34×34), bottom sheet chia sẻ (48×48) | `object-fit: contain`, không bo góc, không đổ bóng |

Không kéo méo, không đổi màu, không đặt mark lên nền đỏ/hổ phách.

---

## 1. Năm nguyên tắc (bất biến thiết kế)

Người dùng chính là **người 55+, đang hoảng, có 2–3 phút trước lúc bấm chuyển tiền**. Mọi lựa chọn thiết kế phải phục vụ tình huống đó.

1. **Chữ to, chạm rộng, tương phản mạnh.** Thân bài tối thiểu 18px, vùng chạm tối thiểu 48px. Không có ngoại lệ vì "cho đẹp".
2. **Không bao giờ có nhãn "An toàn".** Ràng buộc I6 trong kiến trúc. Chỉ có `high` (đỏ) / `medium` (hổ phách) / `unknown` (xám). Màu lục **không** được dùng để nói một tin nhắn là an toàn.
3. **Một màn hình, một hành động chính.** Nút chính luôn cao 64px, đầy màu, nằm cuối luồng đọc.
4. **Nói việc cần làm trước, giải thích sau.** "Đừng chuyển tiền. Đừng đọc mã OTP." đứng trên phần "Vì sao CHẮN nghi ngờ".
5. **Riêng tư phải nhìn thấy được.** Mỗi màn có thu thập dữ liệu đều kèm một hộp `#EAF0FC` nói rõ máy làm gì và không làm gì.

---

## 2. Màu

### 2.1 Thang xanh CHẮN (bảng riêng — phải tự định nghĩa)

Đây là thang duy nhất **không** có sẵn trong Tailwind. Copy nguyên văn.

| Token | Hex | Dùng cho |
|---|---|---|
| `--ink-50` | `#F5F8FE` | Nền màn hình app; chữ trên nền xanh đậm |
| `--ink-100` | `#EAF0FC` | Nền hộp thông tin, chip, tab đang chọn, khối transcript |
| `--ink-200` | `#DCE6F8` | Đường kẻ trên thanh tab; chữ phụ trên panel xanh đậm |
| `--ink-300` | `#C3D2EE` | Viền mặc định của thẻ và nút phụ |
| `--ink-400` | `#93A6CC` | Trạng thái tắt/không hoạt động, viền textarea, chấm "chưa đủ căn cứ" |
| `--ink-500` | `#6B7C9E` | Chữ phụ, caption, nhãn eyebrow |
| `--ink-600` | `#4A5B85` | Chữ thân bài |
| `--ink-700` | `#33436B` | Tiêu đề mục, chữ nhấn |
| `--brand` | `#26339E` | **Màu chủ đạo** — tiêu đề, nút chính, viền nhấn, icon |
| `--brand-raised` | `#3A49C0` | Lớp nổi *bên trong* khối `--brand` (ô icon, thẻ câu hỏi) |

### 2.2 Thang ngữ nghĩa (trùng khớp Tailwind — dùng thẳng)

Nếu dự án dùng Tailwind thì không cần khai báo gì thêm, ba thang này là `red` / `amber` / `emerald` mặc định.

| Vai trò | 50 | 100 | 200 | 300 | 600 | 700 | 800 | 900 |
|---|---|---|---|---|---|---|---|---|
| **Nguy cơ cao** (`red`) | `#FEF2F2` | `#FEE2E2` | `#FECACA` | `#FCA5A5` | `#DC2626` | `#B91C1C` | `#991B1B` | `#7F1D1D` |
| **Cảnh báo TB** (`amber`) | `#FFFBEB` | `#FEF3C7` | — | `#FCD34D` | `#D97706` | — | `#92400E` | `#78350F` |
| **Trạng thái hệ thống** (`emerald`) | `#ECFDF5` | — | — | `#6EE7B7` | `#059669` | `#047857` | `#065F46` | — |

`emerald-400 #34D399` dùng riêng cho hai chi tiết động: vạch quét OCR và ổ khoá trên thanh URL của PWA.

### 2.3 Màu khung máy

`#0B0B0D` (thân máy, thanh trạng thái, thanh gesture) · `#232326` (viền máy, thanh URL PWA). Chỉ dùng trong khung mô phỏng thiết bị của prototype, **không** dùng trong app thật.

### 2.4 Quy tắc màu rủi ro — đọc kỹ

Đây là chỗ dễ sai nhất và sai thì vi phạm bất biến I6.

| Mức rủi ro | Nền hero | Nhãn pill | Chữ phụ trên hero | Thẻ trong nội dung |
|---|---|---|---|---|
| `high` | `red-600` | `red-800` + chữ trắng | `red-100` | nền `red-50`, viền `red-300` |
| `medium` | `amber-600` | `amber-800` + chữ trắng | `amber-100` | nền `amber-50`, viền `amber-300` |
| `unknown` | *(không có hero)* | — | — | nền `#FFFFFF`, viền `--ink-300`, chấm `--ink-400` |

**Màu lục chỉ được dùng cho ba việc:** (1) trạng thái "Đang bảo vệ bác" trên Trang chủ, (2) các lớp bảo vệ L0/L1 ở màn Bảo vệ & riêng tư, (3) báo OCR đọc thành công. Tuyệt đối không gắn lục cho kết quả phân tích một tin nhắn.

### 2.5 Biến CSS — copy vào `:root`

```css
:root {
  /* Thang xanh CHẮN */
  --ink-50:#F5F8FE;  --ink-100:#EAF0FC; --ink-200:#DCE6F8; --ink-300:#C3D2EE;
  --ink-400:#93A6CC; --ink-500:#6B7C9E; --ink-600:#4A5B85; --ink-700:#33436B;
  --brand:#26339E;   --brand-raised:#3A49C0;

  /* Ngữ nghĩa */
  --danger:#DC2626;  --danger-deep:#991B1B; --danger-text:#7F1D1D;
  --danger-bg:#FEF2F2; --danger-border:#FCA5A5;
  --warn:#D97706;    --warn-deep:#92400E;   --warn-text:#78350F;
  --warn-bg:#FFFBEB;   --warn-border:#FCD34D;
  --ok:#059669;      --ok-deep:#065F46;     --ok-text:#047857;
  --ok-bg:#ECFDF5;     --ok-border:#6EE7B7;  --ok-accent:#34D399;

  /* Bo góc */
  --r-xs:8px; --r-sm:12px; --r-md:14px; --r-lg:16px; --r-xl:18px;
  --r-2xl:20px; --r-sheet:24px; --r-pill:999px;

  /* Đổ bóng — luôn ám xanh thương hiệu, không dùng đen thuần */
  --shadow-raised:0 8px 20px rgba(38,51,158,.28);
  --shadow-float:0 10px 26px rgba(38,51,158,.28);

  /* Chuyển động */
  --ease-enter:cubic-bezier(.16,1,.3,1);
}
```

### 2.6 Chế độ tối

Đã chốt: **có dark mode**, bật/tắt ở màn Cài đặt. Cơ chế trong prototype là ghi đè theo thuộc tính, không phải biến CSS — vì mỗi phần tử trong `.dc.html` mang style nội tuyến. Khi dựng UI thật, ánh xạ thẳng sang biến CSS ở §2.5.

Mỗi phần tử cần đổi màu mang một trong bốn thuộc tính đánh dấu, rồi `[data-theme="dark"]` ghi đè:

| Thuộc tính | Giá trị | Ý nghĩa |
|---|---|---|
| `data-sf` | `card` · `sunk` · `tint` · `ok` · `bad` · `warn` | Nền bề mặt |
| `data-bd` | `1` · `ok` · `bad` · `warn` | Màu viền |
| `data-tc` | `h` · `h2` · `b` · `m` · `bad` · `bad2` · `ok` · `ok2` · `warn` · `warn2` | Màu chữ |
| `data-theme` | `light` · `dark` | Đặt ở gốc khung màn hình |

**Bảng màu tối**

| Vai trò | Sáng | Tối |
|---|---|---|
| Nền màn hình (`sunk`) | `#F5F8FE` | `#0B1220` |
| Nền thẻ (`card`) | `#FFFFFF` | `#17223C` |
| Nền chìm trong thẻ (`sunk`) | `#F5F8FE` | `#111B31` |
| Nền nhấn (`tint`) | `#EAF0FC` | `#243252` |
| Viền mặc định | `#C3D2EE` | `#2E3D61` |
| Chữ tiêu đề thương hiệu (`h`) | `#26339E` | `#BACDF8` |
| Chữ nhấn mạnh (`h2`) | `#33436B` | `#E3EAF9` |
| Chữ thân bài (`b`) | `#4A5B85` | `#BCC9E2` |
| Chữ phụ (`m`) | `#6B7C9E` | `#8EA0C2` |
| Nền/viền/chữ đỏ | `#FEF2F2` / `#FCA5A5` / `#991B1B` | `#2E1519` / `#8E2B2B` / `#FCA5A5` |
| Nền/viền/chữ hổ phách | `#FFFBEB` / `#FCD34D` / `#92400E` | `#2C2110` / `#8A5A12` / `#FCD34D` |
| Nền/viền/chữ lục | `#ECFDF5` / `#6EE7B7` / `#065F46` | `#0E2A22` / `#1C6B52` / `#6EE7B7` |
| Nền nút chính | `#26339E` | `#3B4BD4` |
| Viền nhấn nút | `#26339E` | `#5D6EEE` |
| Nút chính bị vô hiệu | `#93A6CC` | `#3A4A70` |
| Chữ tab không hoạt động | `#93A6CC` | `#7E90B8` |

**Hai quy tắc bắt buộc.** Một, mọi nền màu thương hiệu ở chế độ tối dùng `#3B4BD4`, **không** dùng `#26339E` — màu sáng quá tối trên nền `#0B1220` và tụt tương phản. Hai, thang rủi ro ở §2.4 giữ nguyên *vai trò*: đỏ vẫn là `high`, hổ phách vẫn là `medium`, lục vẫn tuyệt đối không gắn với kết quả phân tích tin nhắn.

Khung thiết bị (`#0B0B0D`, `#232326`) và thanh trạng thái **không** đổi theo theme.

---

## 3. Chữ

**Font:** `Inter`, dự phòng `-apple-system, "SF Pro Text", system-ui, sans-serif`. Nạp các nét `400 / 500 / 600 / 700 / 800`. Bật `-webkit-font-smoothing: antialiased`.

| Token | Cỡ | Nét | Line-height | Letter-spacing | Dùng cho |
|---|---|---|---|---|---|
| `hero` | 30px | 800 | 1.22 | −0.6px | Tiêu đề kết quả trên nền đỏ/hổ phách |
| `page-title` | 28px | 800 | 1.25 | −0.5px | Tiêu đề màn hình (Dán tin nhắn, Tra cứu, Bảo vệ) |
| `loading` | 26px | 800 | 1.3 | — | "Đang đọc tin nhắn…" |
| `app-title` | 24px | 800 | 1.3 | −0.5px | Wordmark trên Trang chủ |
| `section` | 22px | 800 | 1.3 | — | Tiêu đề mục trong trang kết quả |
| `cta` | 21px | 800 | — | — | Nút chính; chữ trong ô nhập (nét 600, `+0.5px`) |
| `card-title` | 20px | 700 | 1.3 | — | Tiêu đề thẻ hành động, tiêu đề panel xanh |
| `lead` | 19px | 700 | 1.35 | — | Tên tín hiệu, tên hotline, nút phụ |
| `body` | **18px** | 400–600 | 1.5–1.6 | — | **Cỡ tối thiểu cho câu người dùng phải đọc để ra quyết định** |
| `body-sm` | 17px | 400 | 1.55–1.6 | — | Đoạn giải thích trong thẻ |
| `caption` | 16px | 400–600 | 1.4–1.55 | — | Chú thích dưới tiêu đề thẻ, ghi chú riêng tư |
| `meta` | 15px | 500–700 | — | +0.6px (nếu in hoa) | Dòng nguồn/thời gian, nhãn pill mức rủi ro |
| `eyebrow` | 13–14px | 700 | — | +0.8 → +1.2px | Nhãn in hoa (`NỀN TẢNG`, `MÁY NGHE ĐƯỢC`), nhãn tab, badge nguồn |
| `stat` | 32px | 800 | 1.0 | — | Con số trong ô thống kê |

**Quy tắc 18px, nói cho rõ:** 18px là sàn cho *nội dung quyết định* — nội dung tin nhắn, lời giải thích, cảnh báo, câu hỏi kiểm tra. Nhãn phụ và meta được xuống 15–16px. 13–14px **chỉ** dành cho eyebrow in hoa và nhãn dưới icon tab. Không dùng cỡ nào dưới 13px.

Mọi khối văn xuôi đặt `text-wrap: pretty` để tránh chữ mồ côi cuối dòng.

---

## 4. Khoảng cách, bo góc, đổ bóng

**Khoảng cách:** thang 2px, nhưng thực tế chỉ dùng `6 · 8 · 10 · 12 · 14 · 16 · 18 · 20 · 22 · 24`. Mặc định: gap giữa các thẻ trong danh sách = `10–12px`; gap giữa các khối lớn = `20–22px`.

**Padding nội dung màn hình:** `20px` hai bên là chuẩn. Trang chủ và Bảo vệ dùng `24px 20px 32px`; các màn còn lại `20px 20px 32px`. Hero màu dùng `24px 20px 26px`.

**Bo góc:**

| Giá trị | Dùng cho |
|---|---|
| 8px | Badge nguồn, ô số thứ tự tín hiệu |
| 10px | Nút điều hướng ở sidebar prototype |
| 12px | Ô lồng bên trong panel, chip, nút nhỏ |
| 14px | Ô icon 48×48, thẻ danh sách, nút phụ, tab |
| 16px | Thẻ chính, nút, ô nhập, panel |
| 18px | Panel chế độ nhập (giọng nói / ảnh) |
| 20px | Toast |
| 24px 24px 0 0 | Bottom sheet |
| 999px | Pill, chip |
| 50% | Avatar, chấm trạng thái, nút micro |

**Đổ bóng:** chỉ có hai. `--shadow-raised` cho nút micro, `--shadow-float` cho toast. Cả hai ám xanh `rgba(38,51,158,.28)` — **không dùng bóng đen thuần**, sẽ lệch tông với nền xanh nhạt.

**Vùng chạm:** sàn là **48px**. Nút chính 64px · nút phụ 52–60px · thẻ hành động 76–80px · tab 56px · nút micro 88px.

> ⚠️ **Nợ kỹ thuật đã biết:** nút "‹ Quay lại" / "‹ Trang chủ" trên hero màu hiện là `min-height: 44px`. Khi dựng UI thật phải nâng lên 48px.

---

## 5. Khung màn hình

Hai nền tảng **chỉ khác nhau ở phần chrome trên cùng**. Từ vùng nội dung trở xuống dùng chung 100% — đúng nguyên tắc "App là tập cha của Web" trong kiến trúc.

```
┌─ Thân máy 414×868, r=52px, #0B0B0D, padding 12px ─┐
│ ┌─ Màn hình 390×844, r=42px, nền --ink-50 ──────┐ │
│ │  Chrome trên            (khác theo nền tảng)  │ │
│ │  ┌──────────────────────────────────────────┐ │ │
│ │  │ Nội dung — flex:1, cuộn dọc, ẩn scrollbar│ │ │
│ │  └──────────────────────────────────────────┘ │ │
│ │  Thanh tab dưới  (3 tab, cố định, dùng chung) │ │
│ │  Thanh gesture   (chỉ Android)                │ │
│ └───────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

| Phần | Android | Web PWA |
|---|---|---|
| Chrome trên | Thanh trạng thái 44px, nền `#0B0B0D`, giờ + 4G/pin | Thanh trạng thái 40px + thanh URL 40px (`#232326`, r=20px, ổ khoá `--ok-accent`, nhãn `PWA`) |
| Thanh gesture dưới | Có — 22px, thanh 126×5 `#0B0B0D` | Không |

**Thanh tab dưới (dùng chung):** nền trắng, `border-top: 1px var(--ink-200)`, padding `10px 10px 8px`, gap 6px. Mỗi tab `flex: 1`, cao tối thiểu 56px, bo 14px, icon 24px trên nhãn 13px/700. Tab đang chọn: chữ `--brand` trên nền `--ink-100`; tab thường: chữ `--ink-400`, nền trong suốt.

Bốn tab: **Trang chủ** (nhà) · **Kiểm tra** (kính lúp) · **Bảo vệ** (khiên có dấu tích) · **Cài đặt** (bánh răng). Tab "Kiểm tra" sáng cho cả 4 màn thuộc luồng phân tích và tra cứu.

Khi đang mất mạng, một băng cảnh báo tràn viền chèn vào **giữa chrome trên và vùng nội dung** (xem §7). Nó đẩy nội dung xuống chứ không phủ lên.

---

## 6. Bản đồ màn hình

Tám trạng thái. Mọi màn vào bằng `animation: chanEnter .3s var(--ease-enter) both`.

| # | Màn | Khoá state | Đặc điểm layout |
|---|---|---|---|
| 1 | Trang chủ | `home` | Header logo+lời chào → thẻ trạng thái lục → 2 thẻ hành động → danh sách "Gần đây" |
| 2 | Dán tin nhắn | `input` | Nút quay lại → tiêu đề → 2 thẻ chọn chế độ → panel giọng nói **hoặc** ảnh → ô soạn thảo → nút chính → hộp riêng tư |
| 3 | Chia sẻ từ Zalo | `share` | Overlay `rgba(38,51,158,.55)`, bottom sheet neo đáy, tay cầm 44×5 |
| 4 | Đang phân tích | `loading` | Padding `120px 32px`, chấm 72px nhấp nháy, canh giữa |
| 5 | Kết quả nguy cơ cao | `result` | Hero đỏ → thẻ nguồn → danh sách tín hiệu trúng/trượt → panel xanh câu hỏi → hotline → thẻ đã báo người thân → nút phụ |
| 6 | Tra cứu tài khoản | `check` | Nút quay lại → tiêu đề → 3 pill loại → ô nhập 64px → nút tra cứu → hộp k-Anonymity |
| 7 | Kết quả tra cứu | `checkResult` | Hero hổ phách → 2 ô thống kê → danh sách báo cáo → panel xanh khuyến nghị → hộp miễn trừ |
| 8 | Bảo vệ & riêng tư | `shield` | Tiêu đề → khối lục lớp L0/L1 → danh sách cam kết → thẻ người bảo hộ + nút ngừng chia sẻ |
| 9 | Cài đặt | `settings` | Công tắc chế độ tối → bảng quyền truy cập → khối giả lập lỗi → thẻ người thân |

Toast (nổi trên màn 5, tự ẩn sau 6s) là thành phần riêng, không phải một màn.

---

## 7. Component

Đặc tả rút gọn. Giá trị nào không ghi thì lấy mặc định ở §2–§4.

**Thẻ hành động chính** — cao ≥76px, nền `--brand`, chữ `--ink-50`, bo 16px, gap 16px, padding ngang 20px. Ô icon 48×48 bo 14px nền `--brand-raised`. Tiêu đề 20px/700, phụ đề 16px `--ink-400`.

**Thẻ hành động phụ** — cùng khung, nền trắng, `border: 2px solid var(--brand)`, chữ `--brand`. Ô icon nền `--ink-100`. Phụ đề dùng `--ink-500`.

**Thẻ chọn chế độ** — cao ≥80px, viền 2px. Đang chọn: viền `--brand`, nền `--ink-100`. Không chọn: viền `--ink-300`, nền trắng.

**Nút pill** — `flex: 1`, cao ≥52px, bo 14px, viền 2px, 16px/700. Đang chọn: nền `--brand`, chữ `--ink-50`. Không: nền trắng, viền `--ink-300`, chữ `--ink-600`.

**Nút chính (CTA)** — rộng 100%, cao ≥64px, bo 16px, không viền, 21px/800, chữ trắng. Nút "Kiểm tra ngay" đặc biệt dùng nền `--danger` khi có nội dung và `--ink-400` khi rỗng (vô hiệu) — cố ý, vì đây là hành động khẩn.

**Ô nhập** — cao ≥64px, viền 2px `--brand`, bo 16px, padding ngang 18px, chữ 21px/600 `+0.5px`.
**Ô soạn thảo** — cao 170px, viền 2px `--ink-400`, bo 16px, padding 16px, chữ 18px/1.55, `resize: none`.

**Hero rủi ro** — tràn viền, padding `24px 20px 26px`. Thứ tự bắt buộc: nút quay lại → pill mức rủi ro (bo 999px, `padding 8px 16px`, 15px/700, `+0.6px`, in hoa) → tiêu đề 30px/800 → dòng hành động 19px.

**Thẻ tín hiệu trúng** — nền `--danger-bg`, viền 1px `--danger-border`, bo 14px, padding 16px. Ô "!" 26×26 bo 8px nền `--danger`. Tên 19px/700 `--danger-deep`, lý do 17px `--danger-text`.
**Thẻ tín hiệu trượt** — nền `--ink-50`, viền `--ink-300`, ô "–" nền `--ink-300`, chữ `--ink-600`/`--ink-500`.

**Trích dẫn bằng chứng** — nền trắng, `border-left: 4px solid var(--danger)`, bo `0 10px 10px 0`, padding `10px 12px`, 16px in nghiêng, bọc trong dấu ngoặc kép cong `“ ”`.

**Panel khuyến nghị** — nền `--brand`, bo 16px, padding 20px. Tiêu đề 20px/800 `--ink-50`. Mục con: nền `--brand-raised`, bo 12px, padding `14px 16px`, chữ 18px `--ink-200`. Ghi chú cuối 16px `--ink-400`.

**Dòng hotline** — cao ≥60px, viền 2px `--brand`, bo 14px, nền trắng. Icon → (tên 19px/700 + ghi chú 16px) → số 20px/800 canh phải.

**Ô thống kê** — `flex: 1`, viền 1px `--ink-300`, bo 14px, padding 16px. Số 32px/800 (`--warn` hoặc `--brand`), nhãn 16px `--ink-600`.

**Hộp thông tin** — nền `--ink-100`, bo 14px, padding 16px, gap 12px, icon + chữ 16px `--ink-600`. Dùng cho mọi lời hứa riêng tư.

**Chip** — nền `--ink-100`, bo 999px, `padding 8px 14px`, 15px/600 `--ink-700`.

**Toast** — neo `top: 58px`, `left/right: 14px`, nền trắng, bo 20px, `--shadow-float`, `z-index: 20`. Mark 34px + (nhãn 14px `--ink-500` / tiêu đề 17px/700 `--brand`) + nút đóng tròn 30px. Hàng hành động thụt lề trái 46px.

**Bottom sheet** — overlay `rgba(38,51,158,.55)`, tấm nền `--ink-50` bo `24px 24px 0 0`, padding `20px 20px 28px`, tay cầm 44×5 `--ink-300` canh giữa. Nút "Huỷ" cố định 120px, nút xác nhận `flex: 1`.

**Vùng tải ảnh** — cao ≥180px, `border: 2px dashed var(--ink-400)`, bo 16px, nền `--ink-50`, nội dung canh giữa theo cột.

**Hộp lỗi** — `border: 2px solid var(--danger)`, nền `--danger-bg`, bo 16px, padding 18px. Bố cục: icon tròn cảnh báo 24px + (tiêu đề 19px/800 `--danger-deep` / mô tả 17px `--danger-text`), rồi hàng nút cao ≥52px gồm nút khắc phục (nền `--danger`, chữ trắng, `flex: 1`) và nút "Đóng" (nền trắng, viền `--ink-300`, cố định 108px).

Đặt hộp lỗi **ngay dưới phần mô tả của màn hình, trên nội dung chính** — không dùng modal, không dùng toast. Người 55+ dễ bỏ lỡ thứ tự biến mất, và lỗi ở đây luôn là thứ chặn hành động kế tiếp.

**Băng mất mạng** — dải tràn viền ngay dưới thanh trạng thái, nền `--warn`, chữ trắng 16px/700, icon 20px. Đây là *trạng thái hệ thống*, không phải mức rủi ro `medium` — nên nó nằm ngoài khung màn hình nội dung và không bao giờ xuất hiện cùng lúc với hero hổ phách.

### 7.1 Danh mục lỗi

Bốn lỗi, mỗi lỗi một hành động khắc phục cụ thể. Không có lỗi nào chỉ hiện "Đã có lỗi xảy ra".

| Khoá | Tiêu đề | Khi nào | Nút khắc phục |
|---|---|---|---|
| `mic` | Không dùng được micro | Người dùng chưa cấp quyền micro | Mở quyền micro |
| `micMissing` | Không tìm thấy micro | Thiết bị không có micro | Gửi ảnh thay → chuyển sang chế độ ảnh |
| `ocr` | Không đọc được chữ trong ảnh | OCR thất bại | Chụp lại → về trạng thái chọn ảnh |
| `offline` | Mất mạng | Bấm tra cứu khi không có mạng | Thử lại |

**Nguyên tắc viết lỗi:** nói cái gì hỏng bằng lời thường, rồi cho **một đường thoát khác** ngay trong câu. Ví dụ lỗi micro nói "hoặc dán chữ thay vì nói" — người dùng không bị kẹt vì một kênh nhập liệu hỏng.

Lỗi mất mạng phải nói rõ cái gì **vẫn chạy**: "CHAN vẫn quét được 128 quy tắc trên máy, nhưng chưa tra được danh sách tài khoản." Đây là hệ quả trực tiếp của kiến trúc L1 chạy offline — đừng viết thành "không dùng được".

### 7.2 Giả lập lỗi (chỉ trong prototype)

Màn Cài đặt có khối "Thử tình huống lỗi" với 4 công tắc: mất mạng · chặn micro · máy không có micro · ảnh không đọc được. Bật công tắc rồi thao tác bình thường thì lỗi tương ứng sẽ nổi lên đúng chỗ.

Khối này **chỉ tồn tại trong prototype để demo và user test** — không đưa vào bản dựng thật.

---

## 8. Icon

Toàn bộ là **SVG nội tuyến**, không dùng icon font, không dùng thư viện ngoài.

```
viewBox="0 0 24 24"  fill="none"  stroke="currentColor"
stroke-width="1.9"   stroke-linecap="round"  stroke-linejoin="round"
```

Cỡ mặc định 24×24. Ngoại lệ: micro lớn 38px (`stroke-width: 1.8`), biểu tượng tải ảnh 40px (`stroke-width: 1.6`). Luôn `currentColor` để icon thừa kế màu chữ của khối cha — không hardcode màu vào SVG.

---

## 9. Chuyển động

| Keyframe | Thời lượng | Easing | Dùng cho |
|---|---|---|---|
| `chanEnter` | .3s | `--ease-enter` | Chuyển màn (mờ + trượt lên 10px) |
| `chanDrop` | .32s | `--ease-enter` | Toast rơi từ trên xuống |
| `chanPulse` | 2.4s / 1.4s | `ease-in-out` | Chấm "đang bảo vệ" (2.4s) · chấm đang phân tích (1.4s) |
| `chanRing` | 1.6s | `ease-out` | Vòng lan quanh micro khi đang ghi |
| `chanWave` | .9s | `ease-in-out` | 6 vạch sóng âm, lệch pha `.12s` mỗi vạch |
| `chanScan` | 1.2s | `linear` | Vạch quét OCR (`--ok-accent`) |

Chỉ animate `opacity` và `transform`. Tôn trọng `prefers-reduced-motion`: tắt `chanPulse`, `chanRing`, `chanWave`, `chanScan`; giữ `chanEnter`/`chanDrop` nhưng rút còn 0.01s. **Đã triển khai trong prototype.**

Lưu ý khi tắt animation: ba hiệu ứng cần giá trị dự phòng, nếu không sẽ hỏng bố cục.

| Hiệu ứng | Vì sao cần dự phòng | Giá trị |
|---|---|---|
| `chanWave` | Chiều cao vạch sóng do animation sinh ra — tắt đi thì cao 0, biến mất | `height: 22px` |
| `chanRing` | Vòng lan là hình tròn đỏ đặc, tắt animation thì che kín nút micro | `opacity: 0` |
| `chanScan` | Vạch quét định vị bằng `top` động, tắt đi thì dạt lên đỉnh khung | `top: 50%` |

---

## 10. Tiếp cận (a11y)

- Xưng hô: gọi người dùng là **"bác"**, xưng **"CHẮN"** hoặc "máy". Không dùng "bạn", "người dùng", "quý khách".
- Câu ngắn, một ý một câu. Không thuật ngữ kỹ thuật trong luồng chính (`k-Anonymity` chỉ xuất hiện dưới dạng chip giải thích, kèm câu tiếng Việt thường bên trên).
- Tương phản: mọi cặp chữ/nền trong file này đạt tối thiểu WCAG AA. Không đặt `--ink-400` lên nền trắng cho chữ cần đọc.
- Không truyền tải thông tin **chỉ** bằng màu: mọi mức rủi ro đều kèm nhãn chữ ("NGUY CƠ CAO") và biểu tượng (`!` / `–` / chấm).
- Ẩn scrollbar (`::-webkit-scrollbar { width:0 }`) nhưng **không** chặn cuộn bằng bàn phím.
- Mọi nút phải có nhãn văn bản đọc được; icon đơn độc phải có `aria-label`.

---

## 11. Giọng văn

| Nên | Không nên |
|---|---|
| "Đừng chuyển tiền. Đừng đọc mã OTP." | "Cảnh báo: giao dịch có rủi ro cao." |
| "Máy chỉ gửi 6 ký tự đầu của mã rút gọn." | "Hệ thống áp dụng k-anonymity prefix hashing." |
| "Chưa đủ căn cứ" | "An toàn" / "Không phát hiện rủi ro" |
| "Bác muốn kiểm tra gì?" | "Chọn chức năng" |
| "Họ né trả lời và hối thúc — lúc đó nên cúp máy." | "Nếu đối tượng có biểu hiện lảng tránh…" |

Luôn kèm câu miễn trừ ở kết quả tra cứu: *"Đây là báo cáo của người dùng, không phải kết luận chính thức. Không có báo cáo **không có nghĩa là an toàn**."*

---

## 12. Tám tín hiệu thao túng

Thứ tự hiển thị cố định như dưới. Trúng thì render thẻ đỏ (có trích dẫn bằng chứng), trượt thì render thẻ xám. Tiêu đề mục luôn là "Trúng **N/8** dấu hiệu thao túng".

| # | Tín hiệu |
|---|---|
| 1 | Mạo danh cơ quan chức năng |
| 2 | Doạ hậu quả pháp lý |
| 3 | Ép gấp về thời gian |
| 4 | Yêu cầu giữ bí mật |
| 5 | Đòi mã OTP |
| 6 | Yêu cầu chuyển tiền |
| 7 | Đường link giả mạo |
| 8 | Hứa lợi ích bất thường |

Định nghĩa và cụm từ khoá nằm ở [`codebase/ml/`](../codebase/ml/README.md) — UI **không** được tự định nghĩa lại.

---

## 13. Checklist review PR giao diện

Người review tick đủ 8 ô trước khi approve:

- [ ] Không có mã màu hex viết thẳng trong component — chỉ dùng biến ở §2.5.
- [ ] Không có nhãn "An toàn" / "Safe" / "OK"; màu lục không gắn với kết quả phân tích tin nhắn.
- [ ] Mọi chữ người dùng cần đọc để ra quyết định ≥ 18px.
- [ ] Mọi phần tử bấm được có `min-height` ≥ 48px.
- [ ] Bo góc và khoảng cách lấy từ thang ở §4, không có giá trị lạ.
- [ ] Icon dùng SVG nội tuyến, `stroke-width: 1.9`, `currentColor`.
- [ ] Chuyển động chỉ đụng `opacity`/`transform` và có nhánh `prefers-reduced-motion`.
- [ ] Copy xưng "bác", không có thuật ngữ kỹ thuật lọt vào luồng chính.
- [ ] Đã xem ở **cả hai theme**; không còn nền thương hiệu `#26339E` lọt vào chế độ tối (phải là `#3B4BD4`).
- [ ] Mọi lỗi mới đều có tiêu đề bằng lời thường + một đường thoát khác; không có "Đã có lỗi xảy ra".

---

## 14. Ký chốt

Ký vào đây nghĩa là: bạn đã đọc §1–§4 và sẽ không tự thêm màu/cỡ chữ/bo góc ngoài file này mà không mở PR sửa file này trước.

| Thành viên | Vai trò | Ngày đọc | Đồng ý |
|---|---|---|---|
| | | | ☐ |
| | | | ☐ |
| | | | ☐ |
| | | | ☐ |
| | | | ☐ |

---

## 15. Chưa chốt — cần nhóm quyết

Quyết xong thì cập nhật thẳng vào file này và xoá khỏi mục 15.

**Đã chốt (v1.1):** ~~Chế độ tối~~ → §2.6 · ~~Trạng thái lỗi~~ → §7.1

Còn lại hai điểm:

1. **Cỡ chữ động.** Chưa quyết có tôn trọng `font-scale` của hệ điều hành hay không. Nếu có thì mọi `height` cố định ở §7 phải đổi sang `min-height`.
2. **Nút quay lại 44px.** Nợ kỹ thuật ở §4 — nâng lên 48px hay giữ nguyên vì nằm trên hero màu đã đủ tương phản.

Hai điểm mới phát sinh từ v1.1:

3. **Theo hệ điều hành hay tự chọn?** Hiện dark mode chỉ bật bằng tay ở Cài đặt. Cần quyết có đọc `prefers-color-scheme` làm mặc định lần đầu hay không.
4. **Tương phản bảng màu tối.** Các cặp màu ở §2.6 chưa được đo WCAG như bảng sáng. Cần một lượt kiểm tra trước khi chốt cứng.
