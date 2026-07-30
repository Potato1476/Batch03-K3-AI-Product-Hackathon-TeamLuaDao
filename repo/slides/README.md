# Slide demo — CHẮN

Nguồn của [`../demo-slides.pdf`](../demo-slides.pdf): 6 slide 16:9 cho phần trình
bày **5 phút**. Sinh bằng code, không phải file PowerPoint, để deck diff được như
phần còn lại của repo và mọi con số vẫn ghim vào nguồn.

```bash
python3 repo/slides/build_deck.py
```

Ghi đè thẳng `repo/demo-slides.pdf` — đúng tên file mà `02-guide.md` §5.1 yêu cầu
trong bản nộp. Thêm `--png` nếu cần ảnh từng trang (2400×1350) để dán vào chỗ
khác; PNG không commit.

## Sáu slide, mỗi slide một ý

| # | Ý duy nhất của slide | Nguồn số |
|---|---|---|
| 01 | CHẮN là gì, cho ai | — |
| 02 | Bài toán: 2–3 phút không có cách nào tự kiểm chứng | `spec.md` §1 · `evidence/mining-results.json` |
| 03 | Kiến trúc: sáu tầng L0–L5, một cửa lọc trên máy | `docs/CHAN-ARCHITECTURE.md` §3 |
| 04 | Cách chấm: 8 dấu hiệu có trọng số → 3 mức rủi ro | `docs/CHAN-ARCHITECTURE.md` §5, §6 |
| 05 | Số đo, và ba chỗ còn hỏng | `eval/results.md` |
| 06 | Link demo production + ba thứ nên thử | https://chan-flame.vercel.app |

Kịch bản nói từng trang, kèm phần "cả nhóm phải trả lời được" và backup demo:
[`../demo-slides.md`](../demo-slides.md).

## Ba luật ràng buộc code

1. **Một ý cho mỗi slide.** 5 phút chia cho 6 slide là 50 giây. Thứ gì người nói
   nói được thì không lên slide — slide chỉ neo ý, không thay lời.
2. **Một màu nhấn.** Đỏ chỉ được dùng cho thứ thật sự phải cảnh báo, cả bộ 6 slide
   dùng đúng 4 lần. Mọi thứ khác là mực đen hoặc xám.
3. **Ba mặt chữ, mỗi mặt một việc** — và cả ba đều phủ đủ dấu tiếng Việt. Đã quét
   toàn bộ thư viện font: quá nửa số face phổ biến thiếu 37–42 glyph dấu, loại
   thẳng Outfit, Instrument Sans, Geist Mono.

   | Mặt chữ | Việc |
   |---|---|
   | Big Shoulders Bold | con số / chữ khắc lớn, mỗi slide đúng một lần |
   | IBM Plex Mono | nhãn, đơn vị, chú thích nhỏ |
   | Work Sans | câu được phép nói trọn vẹn |

## Hai phép tự kiểm lúc build

1. **Kiểm lề** — mọi chuỗi chữ vượt ra ngoài lề 68pt đều bị in ra.
2. **Kiểm khoảng hở của dấu** — chữ hoa tiếng Việt đội dấu (Ắ, Ú, Ố) cao hơn hẳn
   chiều cao chữ hoa, nên `ink_top()` đọc thẳng `yMax` của từng glyph thay vì ước
   lượng. Ước lượng đã làm dấu sắc của CHẮN đâm qua đường kẻ đầu trang hai lần
   trước khi có hàm này.

Cả hai phải im lặng thì bản build mới coi là sạch.
