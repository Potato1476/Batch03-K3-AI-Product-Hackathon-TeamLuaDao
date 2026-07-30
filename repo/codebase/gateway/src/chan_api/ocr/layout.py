"""Turn OCR boxes into a conversation.

A chat screenshot carries who-said-what in its geometry, not in its words:
every messenger draws the other person's bubbles against the left edge and the
user's own against the right. Plain OCR throws that away and returns a flat
wall of text, which is exactly the information L5 needs to compare a contact
against their own past.

So the sender is recovered from where a line sits across the image width. This
is a guess, and it is presented to the user as one — the client lets them flip
any line before the thread is analysed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

Sender = Literal["contact", "user"]

#: A line whose centre sits left of this fraction of the width belongs to the
#: other person; right of `_USER_EDGE`, to the user. Between the two the layout
#: is not saying anything, so the neighbours decide.
_CONTACT_EDGE = 0.45
_USER_EDGE = 0.55

#: Lines further apart than this fraction of the image height start a new
#: message even when they lean the same way — one bubble, one message.
_BUBBLE_GAP = 0.035


@dataclass(frozen=True)
class OcrLine:
    text: str
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class ThreadMessage:
    sender: Sender
    text: str


def _side(line: OcrLine, page_width: int) -> Sender | None:
    if page_width <= 0:
        return None
    centre = (line.left + line.width / 2) / page_width
    if centre < _CONTACT_EDGE:
        return "contact"
    if centre > _USER_EDGE:
        return "user"
    return None


def lines_to_thread(
    lines: Sequence[OcrLine],
    *,
    page_width: int,
    page_height: int,
) -> list[ThreadMessage]:
    """Group OCR lines into messages and label each with a likely sender."""
    ordered = sorted(
        (line for line in lines if line.text.strip()),
        key=lambda line: (line.top, line.left),
    )
    if not ordered:
        return []

    sides: list[Sender | None] = [_side(line, page_width) for line in ordered]
    # A centred line inherits the nearest confident neighbour rather than
    # defaulting to one side, which would silently invent an attribution.
    for index, side in enumerate(sides):
        if side is not None:
            continue
        before = next((sides[i] for i in range(index - 1, -1, -1) if sides[i]), None)
        after = next(
            (sides[i] for i in range(index + 1, len(sides)) if sides[i]), None
        )
        sides[index] = before or after or "contact"

    gap_limit = max(1, int(page_height * _BUBBLE_GAP)) if page_height > 0 else 0
    messages: list[ThreadMessage] = []
    previous_bottom = None
    for line, side in zip(ordered, sides):
        assert side is not None
        bottom = line.top + line.height
        same_bubble = (
            messages
            and messages[-1].sender == side
            and previous_bottom is not None
            and line.top - previous_bottom <= gap_limit
        )
        text = " ".join(line.text.split())
        if same_bubble:
            merged = f"{messages[-1].text} {text}".strip()
            messages[-1] = ThreadMessage(sender=side, text=merged)
        else:
            messages.append(ThreadMessage(sender=side, text=text))
        previous_bottom = bottom
    return messages


def parse_tesseract_tsv(tsv: str) -> tuple[list[OcrLine], int, int]:
    """Read Tesseract's TSV into lines plus the page box.

    Levels: 1 page, 2 block, 3 paragraph, 4 line, 5 word. Words carry the text;
    line boxes come from level 4; the page box from level 1.
    """
    rows = tsv.splitlines()
    if not rows:
        return [], 0, 0
    header = rows[0].split("\t")
    try:
        index = {name: header.index(name) for name in
                 ("level", "block_num", "par_num", "line_num", "left", "top",
                  "width", "height", "conf", "text")}
    except ValueError:
        return [], 0, 0

    page_width = page_height = 0
    boxes: dict[tuple[str, str, str], tuple[int, int, int, int]] = {}
    words: dict[tuple[str, str, str], list[str]] = {}
    for row in rows[1:]:
        columns = row.split("\t")
        if len(columns) <= index["text"]:
            continue
        level = columns[index["level"]]
        if level == "1":
            page_width = int(columns[index["width"]] or 0)
            page_height = int(columns[index["height"]] or 0)
            continue
        key = (
            columns[index["block_num"]],
            columns[index["par_num"]],
            columns[index["line_num"]],
        )
        if level == "4":
            boxes[key] = (
                int(columns[index["left"]] or 0),
                int(columns[index["top"]] or 0),
                int(columns[index["width"]] or 0),
                int(columns[index["height"]] or 0),
            )
        elif level == "5":
            try:
                confidence = float(columns[index["conf"]])
            except ValueError:
                confidence = -1.0
            text = columns[index["text"]].strip()
            if text and confidence >= 0:
                words.setdefault(key, []).append(text)

    lines = [
        OcrLine(text=" ".join(tokens), left=box[0], top=box[1], width=box[2], height=box[3])
        for key, tokens in words.items()
        if (box := boxes.get(key)) is not None
    ]
    return lines, page_width, page_height
