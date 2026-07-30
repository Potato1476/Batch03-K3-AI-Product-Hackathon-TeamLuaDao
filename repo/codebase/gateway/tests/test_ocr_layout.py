"""Recovering who-said-what from a chat screenshot's geometry."""

from __future__ import annotations

from chan_api.ocr.layout import OcrLine, lines_to_thread, parse_tesseract_tsv

PAGE_WIDTH = 1000
PAGE_HEIGHT = 2000


def line(text: str, left: int, top: int, width: int = 300, height: int = 40) -> OcrLine:
    return OcrLine(text=text, left=left, top=top, width=width, height=height)


def test_left_bubbles_are_the_contact_and_right_bubbles_are_the_user():
    messages = lines_to_thread(
        [
            line("Chào cậu dạo này thế nào", 40, 100),
            line("Tớ vẫn ổn cậu sao rồi", 660, 200),
            line("cho a muon 5 trieu voi", 40, 300),
        ],
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )
    assert [message.sender for message in messages] == ["contact", "user", "contact"]
    assert messages[2].text == "cho a muon 5 trieu voi"


def test_lines_are_ordered_top_to_bottom_regardless_of_ocr_order():
    messages = lines_to_thread(
        [
            line("tin thứ ba", 40, 500),
            line("tin thứ nhất", 40, 100),
            line("tin thứ hai", 660, 300),
        ],
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )
    assert [message.text for message in messages] == [
        "tin thứ nhất",
        "tin thứ hai",
        "tin thứ ba",
    ]


def test_a_wrapped_bubble_becomes_one_message():
    """Two lines, same side, touching — that is one bubble, not two messages."""
    messages = lines_to_thread(
        [
            line("em dang ket tien qua, ck giup a", 40, 100),
            line("15 trieu vao stk 0912345678", 40, 142),
        ],
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )
    assert len(messages) == 1
    assert messages[0].text == "em dang ket tien qua, ck giup a 15 trieu vao stk 0912345678"


def test_a_vertical_gap_starts_a_new_message_on_the_same_side():
    messages = lines_to_thread(
        [
            line("Chào cậu", 40, 100),
            line("cho a muon 5 trieu", 40, 600),
        ],
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )
    assert len(messages) == 2


def test_a_centred_line_inherits_a_neighbour_instead_of_defaulting():
    messages = lines_to_thread(
        [
            line("tin bên phải", 660, 100),
            line("dòng ở giữa", 380, 400, width=240),
        ],
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )
    assert [message.sender for message in messages] == ["user", "user"]


def test_empty_input_yields_no_messages():
    assert lines_to_thread([], page_width=PAGE_WIDTH, page_height=PAGE_HEIGHT) == []
    assert lines_to_thread(
        [line("   ", 40, 100)], page_width=PAGE_WIDTH, page_height=PAGE_HEIGHT
    ) == []


TSV = "\t".join(
    ["level", "page_num", "block_num", "par_num", "line_num", "word_num",
     "left", "top", "width", "height", "conf", "text"]
)


def _row(level, block, par, line_num, left, top, width, height, conf, text):
    return "\t".join(
        str(value)
        for value in [level, 1, block, par, line_num, 1, left, top, width, height, conf, text]
    )


def test_tesseract_tsv_is_parsed_into_lines_and_a_page_box():
    tsv = "\n".join(
        [
            TSV,
            _row(1, 0, 0, 0, 0, 0, 1080, 1920, -1, ""),
            _row(4, 1, 1, 1, 40, 100, 300, 40, -1, ""),
            _row(5, 1, 1, 1, 40, 100, 140, 40, 92, "Chào"),
            _row(5, 1, 1, 1, 190, 100, 150, 40, 90, "cậu"),
            _row(4, 2, 1, 1, 660, 200, 300, 40, -1, ""),
            _row(5, 2, 1, 1, 660, 200, 300, 40, 88, "Ừ"),
        ]
    )
    lines, width, height = parse_tesseract_tsv(tsv)
    assert (width, height) == (1080, 1920)
    assert {line.text for line in lines} == {"Chào cậu", "Ừ"}


def test_low_confidence_words_are_dropped():
    tsv = "\n".join(
        [
            TSV,
            _row(1, 0, 0, 0, 0, 0, 1080, 1920, -1, ""),
            _row(4, 1, 1, 1, 40, 100, 300, 40, -1, ""),
            _row(5, 1, 1, 1, 40, 100, 140, 40, -1, "rác"),
        ]
    )
    lines, _, _ = parse_tesseract_tsv(tsv)
    assert lines == []


def test_malformed_tsv_does_not_raise():
    assert parse_tesseract_tsv("") == ([], 0, 0)
    assert parse_tesseract_tsv("không phải tsv") == ([], 0, 0)
