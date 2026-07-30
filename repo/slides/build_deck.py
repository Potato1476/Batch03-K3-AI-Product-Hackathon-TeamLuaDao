#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHẮN — bộ 6 slide 16:9 cho demo 5 phút.
Movement: THRESHOLD CARTOGRAPHY (xem DESIGN-PHILOSOPHY.md).

Luật tự áp cho bộ này: **một ý cho mỗi slide.** 5 phút chia cho 6 slide là 50
giây; thứ gì người nói nói được thì không lên slide. Mọi con số còn lại đều
truy được về repo/spec.md, repo/docs/CHAN-ARCHITECTURE.md và repo/eval/results.md.

    python3 build_deck.py          # → ../demo-slides.pdf, kèm hai phép tự kiểm
    python3 build_deck.py --png    # xuất thêm PNG 2400×1350 (không commit)
"""
import os
import sys
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color, HexColor
from fontTools.ttLib import TTFont as GlyphSource

# ──────────────────────────────────────────────────────────────── field & stock

W, H = 960.0, 540.0                 # 16:9
M = 68.0                            # lề bất khả xâm phạm
TOP = H - 56.0                      # đường kẻ duy nhất trên mỗi slide
FLOOR = 74.0                        # sàn của vùng chữ

DECK_URL = "chan-flame.vercel.app"

FONT_DIR = ("/Users/nguyenbao/Library/Application Support/Claude/"
            "local-agent-mode-sessions/skills-plugin/"
            "f8289512-99a4-4784-9db3-75856942b926/"
            "4d7f1b4e-f45a-4406-9e7c-8759c121e3a6/skills/canvas-design/canvas-fonts")

for _n in ("BigShoulders-Bold", "IBMPlexMono-Regular", "IBMPlexMono-Bold",
           "WorkSans-Regular", "WorkSans-Bold"):
    pdfmetrics.registerFont(TTFont(_n, os.path.join(FONT_DIR, _n + ".ttf")))

DISPLAY = "BigShoulders-Bold"
MONO, MONOB = "IBMPlexMono-Regular", "IBMPlexMono-Bold"
SANS, SANSB = "WorkSans-Regular", "WorkSans-Bold"

# ─────────────────────────────────────────────────────────────── calibrated hues

BONE  = HexColor("#EDE6D8")
INK   = HexColor("#17171B")
GREY  = HexColor("#8B8578")
GREY_D = HexColor("#5E5A50")
HAIR  = HexColor("#CDC5B2")
VERM  = HexColor("#C0442C")         # nhân chứng, không phải trang trí
AMBER = HexColor("#BE8A2E")
SLATE = HexColor("#7C8A86")

AUDIT = []
_GLYPHS = {}


def ink_top(s, font, size):
    """Thật sự cao bao nhiêu tính từ đường chân chữ.

    Chữ hoa tiếng Việt đội dấu (Ắ, Ú, Ố) vượt xa chiều cao chữ hoa, nên không
    thể ước lượng bằng cap-height. Đọc thẳng yMax của từng glyph.
    """
    src = _GLYPHS.get(font)
    if src is None:
        src = GlyphSource(os.path.join(FONT_DIR, font + ".ttf"))
        _GLYPHS[font] = src
    upem = src["head"].unitsPerEm
    cmap, glyf = src.getBestCmap(), src["glyf"]
    top = 0
    for ch in s:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        g = glyf[name]
        if g.numberOfContours:
            top = max(top, g.yMax)
    return top * size / upem


def mix(a, b, t):
    return Color(a.red + (b.red - a.red) * t,
                 a.green + (b.green - a.green) * t,
                 a.blue + (b.blue - a.blue) * t)


# ───────────────────────────────────────────────────────────────── instruments

class Slide:
    def __init__(self, c, n, rubric):
        self.c, self.n = c, n
        c.setFillColor(BONE)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        self.rule(M, TOP, W - M, HAIR, 0.5)
        self.txt(M, TOP + 8, rubric, MONO, 6.6, GREY, track=2.4)
        self.txt(W - M, TOP + 8, f"{n:02d} / 06", MONO, 6.6, GREY, track=2.4, align="r")

    # — primitives —

    def rule(self, x1, y, x2, col=HAIR, w=0.5):
        self.c.setStrokeColor(col)
        self.c.setLineWidth(w)
        self.c.setLineCap(0)
        self.c.line(x1, y, x2, y)

    def vrule(self, x, y1, y2, col=HAIR, w=0.5):
        self.c.setStrokeColor(col)
        self.c.setLineWidth(w)
        self.c.line(x, y1, x, y2)

    def bar(self, x, y, w, h, col):
        self.c.setFillColor(col)
        self.c.rect(x, y, w, h, stroke=0, fill=1)

    def width(self, s, font, size, track=0.0):
        return pdfmetrics.stringWidth(s, font, size) + track * max(len(s) - 1, 0)

    def txt(self, x, y, s, font=MONO, size=7.0, col=INK, track=0.0, align="l"):
        wdt = self.width(s, font, size, track)
        if align == "r":
            x -= wdt
        elif align == "c":
            x -= wdt / 2.0
        t = self.c.beginText(x, y)
        t.setFont(font, size)
        t.setFillColor(col)
        t.setCharSpace(track)          # Tc persists in the stream — always emit
        t.textOut(s)
        self.c.drawText(t)
        optical = font == DISPLAY and size > 60      # set to the optical margin
        if not optical and (x < M - 1.5 or x + wdt > W - M + 1.5
                            or y < FLOOR - 34 or y > TOP + 14):
            AUDIT.append((self.n, s[:44], round(x, 1), round(x + wdt, 1), round(y, 1)))
        return wdt

    def display(self, x, y, s, size, col=INK, ceiling=None, track=0.0):
        """Chữ khắc lớn, có kiểm khoảng hở phía trên bằng bao glyph thật."""
        if ceiling is not None:
            top = y + ink_top(s, DISPLAY, size)
            if top > ceiling:
                AUDIT.append((self.n, s[:30], "đội lên", round(top, 1),
                              "trần", round(ceiling, 1)))
        return self.txt(x, y, s, DISPLAY, size, col, track)

    def wrap(self, s, font, size, maxw, track=0.0):
        lines, cur = [], ""
        for wd in s.split(" "):
            trial = wd if not cur else cur + " " + wd
            if self.width(trial, font, size, track) <= maxw:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, font=SANS, size=9.0, lead=13.5, maxw=400,
             col=GREY_D, track=0.0):
        lines = self.wrap(s, font, size, maxw, track)
        for i, ln in enumerate(lines):
            self.txt(x, y - i * lead, ln, font, size, col, track)
        return y - (len(lines) - 1) * lead

    def eyebrow(self, y, s, col=GREY):
        self.bar(M, y + 1.9, 10.0, 1.0, col)
        self.txt(M + 16, y, s, MONOB, 7.0, col, track=3.0)


# ──────────────────────────────────────────────────────────────────── 01 · bìa

def slide_1(c):
    s = Slide(c, 1, "NHÓM LUA DAO · ZONE C · HƯỚNG C")

    s.display(M - 4, 268, "CHẮN", 172, INK, ceiling=TOP - 12, track=-2)
    s.txt(M, 232, "TRỢ LÝ CHỐNG LỪA ĐẢO CHO NGƯỜI 55+",
          MONOB, 10.0, GREY_D, track=6.0)

    s.rule(M, 130, W - M, HAIR, 0.5)
    s.txt(M, 112, "Kiểm tra một tin nhắn đáng ngờ, trước khi bác làm theo.",
          SANS, 10.4, GREY_D)
    s.txt(W - M, 112, DECK_URL, MONOB, 10.4, VERM, align="r")


# ─────────────────────────────────────────────────────────────── 02 · bài toán

def slide_2(c):
    s = Slide(c, 2, "BÀI TOÁN")

    s.eyebrow(430, "NGƯỜI 55+ · ĐANG CẦM MÁY ĐỌC MỘT TIN NHẮN VỪA ĐẾN")

    s.display(M - 4, 290, "2–3 PHÚT", 112, INK, ceiling=418, track=-1)
    s.txt(M, 258, "GIỮA LÚC ĐỌC TIN NHẮN MẠO DANH VÀ LÚC BẤM CHUYỂN TIỀN",
          MONO, 8.2, GREY, track=2.6)

    s.para(M, 198,
           "Trong 2–3 phút đó họ không có cách nào tự kiểm chứng, nên hoặc làm theo, "
           "hoặc phải phiền con cháu.",
           SANS, 15.0, 23.0, 660, INK)

    s.rule(M, 130, W - M, HAIR, 0.5)
    s.txt(M, 112, "15.840 HỘI THOẠI LỪA ĐẢO ĐÃ MINING", MONOB, 7.4, GREY_D, track=1.8)
    s.txt(W - M, 112, "6.391 TỪ 6 NGUỒN PUBLIC DẪN TÊN ĐƯỢC",
          MONO, 7.4, GREY, track=1.8, align="r")


# ────────────────────────────────────────────────────────────── 03 · kiến trúc

def slide_3(c):
    s = Slide(c, 3, "KIẾN TRÚC")

    s.eyebrow(430, "SÁU TẦNG, MỘT CỬA LỌC")

    s.txt(M, 396, "WEB PWA  ·  ANDROID  ·  ZALO OA", MONOB, 8.0, GREY_D, track=2.2)
    s.txt(W - M, 396, "dán chữ · ảnh chụp (OCR) · chia sẻ thẳng từ Zalo",
          MONO, 7.4, GREY, align="r")

    GATE = M + 282
    s.txt(M, 336, "TRÊN MÁY", MONOB, 7.4, GREY, track=2.6)
    s.txt(GATE + 42, 336, "TRÊN MÁY CHỦ", MONOB, 7.4, GREY, track=2.6)

    layers = [(M, "L0", "chuẩn hoá"),
              (M + 130, "L1", "luật · chặn OTP"),
              (GATE + 42, "L2", "ẩn danh hoá"),
              (GATE + 172, "L3", "chấm 8 dấu hiệu"),
              (GATE + 302, "L4", "cộng điểm · ngưỡng"),
              (GATE + 432, "L5", "so cả đoạn chat")]
    for x, code, name in layers:
        s.display(x, 250, code, 74, mix(BONE, INK, 0.88), ceiling=328)
        s.txt(x + 2, 228, name, MONO, 7.6, GREY_D)

    # the gate — the one place the diagram narrows
    s.vrule(GATE, 216, 348, INK, 0.9)
    s.txt(GATE, 202, "CỬA LỌC", MONOB, 7.4, INK, track=2.6, align="c")

    s.rule(M, 170, W - M, HAIR, 0.5)
    s.txt(M, 150, "~95% tin nhắn không bao giờ rời khỏi máy.", SANS, 11.0, INK)
    s.txt(M, 118, "Tin có mã OTP bị chặn cứng ngay trên máy — không gửi byte nào "
                  "lên máy chủ.", SANS, 11.0, VERM)


# ─────────────────────────────────────────────────────────────── 04 · cách chấm

def slide_4(c):
    s = Slide(c, 4, "CÁCH CHẤM")

    s.eyebrow(430, "TÁM DẤU HIỆU THAO TÚNG, CÓ TRỌNG SỐ")

    signals = [("Mạo danh cơ quan thẩm quyền", 0.20),
               ("Yêu cầu giữ bí mật với người thân", 0.20),
               ("Tạo áp lực thời gian", 0.15),
               ("Chuyển tiền vào tài khoản cá nhân", 0.15),
               ("Cài app ngoài store", 0.15),
               ("Hứa lợi ích bất thường", 0.08),
               ("Đề nghị chuyển kênh liên lạc", 0.07),
               ("Yêu cầu mã OTP", None)]
    COLW, GAPX, BARW = 396.0, 32.0, 100.0
    for i, (name, wgt) in enumerate(signals):
        x = M + (i // 4) * (COLW + GAPX)
        y = 392 - (i % 4) * 34
        bx = x + COLW - 56 - BARW
        if wgt is None:
            s.txt(x, y, name, SANS, 10.4, VERM)
            for k in range(13):
                s.bar(bx + k * (BARW / 12.0), y - 1.6, 3.2, 5.0, VERM)
            s.txt(x + COLW, y, "GHI ĐÈ", MONOB, 8.0, VERM, track=1.2, align="r")
        else:
            s.txt(x, y, name, SANS, 10.4, INK)
            s.bar(bx, y - 1.6, BARW, 5.0, mix(BONE, INK, 0.11))
            s.bar(bx, y - 1.6, BARW * (wgt / 0.20), 5.0, mix(BONE, INK, 0.58))
            s.txt(x + COLW, y, f"{wgt:.2f}".replace(".", ","),
                  MONOB, 8.6, INK, align="r")

    # the calibrated band — the whole decision, in one line
    by, bw = 178.0, W - 2 * M
    prev = 0.0
    for frac, col in [(0.35, SLATE), (0.70, AMBER), (1.0, VERM)]:
        s.bar(M + bw * prev, by, bw * (frac - prev), 15.0, col)
        prev = frac
    for lo, hi, code, lab in [(0.0, 0.35, "unknown", "CHƯA PHÁT HIỆN DẤU HIỆU"),
                              (0.35, 0.70, "medium", "CẦN KIỂM TRA THÊM"),
                              (0.70, 1.0, "high", "NHIỀU DẤU HIỆU LỪA ĐẢO")]:
        cx = M + bw * (lo + hi) / 2.0
        s.txt(cx, 224, code, MONOB, 11.0, INK, track=1.6, align="c")
        s.txt(cx, 210, lab, MONO, 7.2, GREY, track=1.4, align="c")
    for frac, lab in [(0.0, "0"), (0.35, "0,35"), (0.70, "0,70"), (1.0, "1,0")]:
        al = "l" if frac == 0 else ("r" if frac == 1.0 else "c")
        x = M + bw * frac
        s.txt(x, 160, lab, MONOB, 7.4, GREY_D, align=al)
        if 0 < frac < 1:
            s.vrule(x, 172, 196, INK, 1.0)

    s.txt(M, 118, "Không có mức “An toàn”. Chỉ ba mức — và một tin đòi mã OTP thì "
                  "ghi đè thẳng lên high.", SANS, 11.0, VERM)


# ───────────────────────────────────────────────────────────────── 05 · số đo

def slide_5(c):
    s = Slide(c, 5, "SỐ ĐO")

    s.eyebrow(430, "QUALITY BAR CHỐT 23:59 NGÀY 1, KHÔNG SỬA SAU ĐÓ")

    cols = [(M, "20/20", "GOLDEN SET · 20 CASE", "bar ≥ 18/20"),
            (M + 292, "93,6%", "RECALL · 125 TIN LỪA ĐẢO", "bar ≥ 90%"),
            (M + 584, "8,2%", "BÁO NHẦM · 73 TIN HỢP LỆ", "bar < 15%")]
    for x, val, cap, bar in cols:
        s.display(x - 3, 316, val, 96, INK, ceiling=418, track=-1)
        s.txt(x, 284, cap, MONOB, 7.6, GREY_D, track=1.6)
        s.txt(x, 270, bar, MONO, 7.6, GREY, track=1.6)

    s.rule(M, 232, W - M, HAIR, 0.5)
    s.eyebrow(212, "ĐẠT BAR KHÔNG CÓ NGHĨA LÀ XONG", VERM)
    s.txt(M, 178, "Tin nhắn học phí thật của nhà trường bị chấm high — báo nhầm "
                  "nguy hiểm nhất.", SANS, 11.0, INK)
    s.txt(M, 152, "L5 đo trên 1.282 hội thoại thật: recall 0. Khai là ngoài lát cắt, "
                  "chưa validate.", SANS, 11.0, INK)
    s.txt(M, 126, "Probe 36 câu soạn độc lập: 22/24 recall, 3/12 báo nhầm — tệ hơn "
                  "hẳn bộ 20 case.", SANS, 11.0, INK)


# ──────────────────────────────────────────────────────────────────── 06 · demo

def slide_6(c):
    s = Slide(c, 6, "DEMO")

    s.eyebrow(430, "CHẠY THẬT, KHÔNG PHẢI BẢN DỰNG SẴN")

    s.display(M - 3, 312, DECK_URL, 86, VERM, ceiling=418, track=-0.5)
    s.txt(M, 278, "MỞ TRÊN ĐIỆN THOẠI — KHÔNG CẦN CÀI APP",
          MONOB, 9.0, GREY_D, track=4.0)

    s.rule(M, 222, W - M, HAIR, 0.5)

    tries = [("DÁN MỘT TIN NHẮN", "“Tôi là cán bộ công an. Bác chuyển tiền xác minh "
                                  "trước 17h và không được nói với người nhà.”"),
             ("GỬI ẢNH CHỤP", "OCR tiếng Việt tự host — chữ đổ vào ô soạn thảo để "
                              "bác sửa trước khi kiểm tra."),
             ("DÁN CẢ ĐOẠN CHAT", "Nghi người quen bị chiếm tài khoản — so cách nhắn "
                                  "hôm nay với chính họ trước đây.")]
    CW = (W - 2 * M - 56) / 3.0
    for i, (head, body) in enumerate(tries):
        x = M + i * (CW + 28)
        if i:
            s.vrule(x - 14, 152, 206, HAIR, 0.5)
        s.txt(x, 200, head, MONOB, 8.0, INK, track=2.0)
        s.para(x, 182, body, SANS, 8.6, 13.0, CW, GREY_D)

    s.rule(M, 130, W - M, HAIR, 0.5)
    s.txt(M, 112, "NHÓM LUA DAO", MONOB, 7.4, GREY_D, track=2.6)
    s.txt(W - M, 112, "DEMO CP6", MONO, 7.4, GREY, track=2.6, align="r")


# ─────────────────────────────────────────────────────────────────────── main

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    # Tên file do 02-guide.md §5.1 quy định — bản nộp phải là repo/demo-slides.pdf.
    out = os.path.join(os.path.dirname(here), "demo-slides.pdf")
    c = rl_canvas.Canvas(out, pagesize=(W, H))
    c.setTitle("CHẮN — Trợ lý chống lừa đảo · Nhóm LuaDao")
    c.setAuthor("Nhóm LuaDao")
    c.setSubject("Threshold Cartography — 6 slide cho demo 5 phút")
    for fn in (slide_1, slide_2, slide_3, slide_4, slide_5, slide_6):
        fn(c)
        c.showPage()
    c.save()
    print("wrote", out)

    if "--png" in sys.argv:                 # bản xuất phụ, không commit
        stem = os.path.join(here, "demo-slides")
        if os.system(f'pdftoppm -png -r 180 "{out}" "{stem}"') == 0:
            for i in range(1, 7):           # pdftoppm đệm số theo tổng số trang
                src = f"{stem}-{i}.png"
                if os.path.exists(src):
                    os.replace(src, f"{stem}-{i:02d}.png")
            print("wrote", stem + "-01…06.png", "(2400 × 1350)")

    if AUDIT:
        print(f"\n!! {len(AUDIT)} phần tử vượt lề:")
        for row in AUDIT:
            print("   ", row)
    else:
        print("kiểm lề: sạch — không phần tử nào vượt lề.")


if __name__ == "__main__":
    main()
