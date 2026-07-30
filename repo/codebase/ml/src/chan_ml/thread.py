"""L5 — conversation-level analysis for hijacked-account scams.

A hijacked Facebook or Zalo account is invisible one message at a time. The
attacker writes from a real account the victim trusts, and the request itself
("chuyển giúp em 5 triệu") is a sentence a real friend could also send. What
gives it away is the *thread*: the person who has been typing one way for
months suddenly types another way, has never asked for money before, and will
not get on a video call.

So this layer does not look at a message. It compares a contact against their
own past, using deterministic features only — no training data exists for this
scenario and inventing some would be worse than measuring what can be measured.

The eight L3 signal codes stay untouched: `mao_danh_tham_quyen` means an
authority claim, and reusing it for a hijacked friend would produce an
explanation that reads like a lie to the user. Thread findings get their own
vocabulary and their own explanation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Literal, Mapping, Sequence

Sender = Literal["contact", "user"]

#: Thread-level findings. Deliberately separate from `SIGNAL_CODES`.
THREAD_SIGNAL_CODES: tuple[str, ...] = (
    "doi_giong_van",
    "yeu_cau_tien_dot_ngot",
    "ne_goi_thoai",
    "tk_khac_ten",
    "gap_va_bi_mat",
)

THREAD_SIGNAL_LABELS: dict[str, str] = {
    "doi_giong_van": "Cách nhắn tin đổi khác so với trước",
    "yeu_cau_tien_dot_ngot": "Lần đầu hỏi tiền trong cả cuộc trò chuyện",
    "ne_goi_thoai": "Né gọi điện hoặc gọi video",
    "tk_khac_ten": "Tên chủ tài khoản khác tên người quen",
    "gap_va_bi_mat": "Vừa thúc gấp vừa xin giữ kín",
}

#: A contact needs at least this many earlier messages before their style can
#: be compared against anything. Below it the honest answer is "not enough to
#: judge" — difficulty class ①, not a quiet pass.
MIN_BASELINE_MESSAGES = 3

#: Style distance above which the way this contact types counts as changed.
#: Chosen so that the same person writing casually vs carefully stays below it;
#: see tests/test_thread.py for the pairs this was checked against.
STYLE_SHIFT_THRESHOLD = 0.34

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]",
    re.UNICODE,
)
_SENTENCE_END = re.compile(r"[.!?…]\s*$")

_ADDRESS_TERMS = frozenset(
    {
        "anh", "chi", "em", "con", "chau", "ba", "ong", "bo", "me", "co", "chu",
        "bac", "cau", "di", "tao", "may", "to", "tui", "minh", "ta", "thay",
    }
)

_MONEY_ASK = re.compile(
    r"(?:"
    r"(?:chuyen|gui|nap|cho\s*muon|muon|vay|ung|chuyen\s*khoan|ck)\s+"
    r"(?:\w+\s+){0,3}?(?:tien|khoan|trieu|tr|k\b|dong|vnd|it|gap)"
    r"|(?:stk|so\s*tai\s*khoan|tai\s*khoan\s+\w+)"
    r"|\d{1,3}(?:[.,]\d{3})*\s*(?:k|tr|trieu|ty|dong|vnd)\b"
    r"|(?:momo|zalopay|vietcombank|vcb|techcombank|bidv|mbbank|agribank)"
    r")",
    re.UNICODE,
)

_CALL_REFUSAL = re.compile(
    r"(?:"
    r"(?:khong|ko|k)\s*(?:the\s*)?(?:goi|nghe|video|facetime|call)"
    r"|(?:dang|ban)\s*(?:hop|lai\s*xe|o\s*ngoai|ban\s*lam)"
    r"|(?:mic|micro|loa|cam|camera|may)\b(?:\s+\w+){0,2}?\s*(?:bi\s*)?(?:hong|hu|loi|vo)\b"
    r"|(?:mat|het)\s*song"
    r"|nhan\s*tin\s*(?:thoi|di|nhe|cho\s*tien)"
    r"|(?:goi|call)\s*sau"
    r")",
    re.UNICODE,
)

_CALL_REQUEST = re.compile(
    r"(?:goi\s*(?:dien|video|face)|video\s*call|facetime|nghe\s*may|alo\s*cai)",
    re.UNICODE,
)

_SECRECY = re.compile(
    r"(?:dung\s*(?:noi|ke)|khong\s*(?:noi|ke)|giu\s*(?:bi\s*mat|kin)"
    r"|bi\s*mat|xoa\s*tin\s*nhan|dung\s*hoi\s*ai)",
    re.UNICODE,
)

_URGENCY = re.compile(
    r"(?:gap(?!\s*(?:lai|nhau|mat|anh|chi|em|bac|con|bo|me|ban))"
    r"|ngay\s*bay\s*gio|lien\s*ngay|nhanh\s*len|trong\s*hom\s*nay|keo\s*muon)",
    re.UNICODE,
)

#: "chủ tài khoản là Nguyễn Văn A" / "tên Nguyễn Văn A"
_ACCOUNT_NAME = re.compile(
    r"(?:chu\s*tai\s*khoan|ten\s*(?:tai\s*khoan|tk|nguoi\s*nhan)?)\s*(?:la|:)?\s*"
    r"((?:[a-z]+\s+){1,3}[a-z]+)",
    re.UNICODE,
)


def _strip_diacritics(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d").replace("Đ", "D")


def _fold(text: str) -> str:
    """Lowercase, drop diacritics, collapse spaces — matching form only."""
    return " ".join(_strip_diacritics(text.lower()).split())


@dataclass(frozen=True)
class ThreadMessage:
    sender: Sender
    text: str


@dataclass(frozen=True)
class ThreadSignal:
    code: str
    confidence: float
    evidence: str


@dataclass(frozen=True)
class ThreadAnalysis:
    risk: str
    thread_signals: tuple[ThreadSignal, ...]
    explanation: str
    questions: tuple[str, ...]
    baseline_messages: int
    style_distance: float | None
    ask_message_index: int | None
    #: True when the contact has too little history to compare against.
    insufficient_history: bool = False
    detail: Mapping[str, float] = field(default_factory=dict)


def _style_profile(messages: Sequence[str]) -> dict[str, float]:
    """Six cheap, language-appropriate habits of one person's typing."""
    if not messages:
        return {}
    letters = diacritics = emoji = 0
    words: list[str] = []
    ends_punctuated = starts_upper = 0
    address_used: set[str] = set()
    for message in messages:
        tokens = _WORD.findall(message)
        words.extend(tokens)
        for token in tokens:
            folded = _strip_diacritics(token.lower())
            if folded in _ADDRESS_TERMS:
                address_used.add(folded)
        for character in message:
            if character.isalpha():
                letters += 1
                if _strip_diacritics(character) != character:
                    diacritics += 1
        emoji += len(_EMOJI.findall(message))
        if _SENTENCE_END.search(message.strip()):
            ends_punctuated += 1
        stripped = message.strip()
        if stripped and stripped[0].isupper():
            starts_upper += 1
    count = len(messages)
    return {
        "diacritic_ratio": diacritics / letters if letters else 0.0,
        "avg_words": len(words) / count,
        "emoji_per_message": emoji / count,
        "ends_punctuated": ends_punctuated / count,
        "starts_upper": starts_upper / count,
        "address_terms": address_used,  # type: ignore[dict-item]
    }


def _style_distance(before: Mapping[str, object], after: Mapping[str, object]) -> float:
    """0 = types identically, 1 = nothing in common. Bounded per feature."""
    if not before or not after:
        return 0.0
    numeric = (
        ("diacritic_ratio", 1.0),
        ("emoji_per_message", 2.0),
        ("ends_punctuated", 1.0),
        ("starts_upper", 1.0),
    )
    parts = [
        min(1.0, abs(float(before[key]) - float(after[key])) / scale)  # type: ignore[arg-type]
        for key, scale in numeric
    ]
    # Message length is compared in relative terms: doubling matters, +2 words
    # on an already long message does not.
    long_before = float(before["avg_words"])  # type: ignore[arg-type]
    long_after = float(after["avg_words"])  # type: ignore[arg-type]
    longest = max(long_before, long_after, 1.0)
    parts.append(min(1.0, abs(long_before - long_after) / longest))

    terms_before: set[str] = before["address_terms"]  # type: ignore[assignment]
    terms_after: set[str] = after["address_terms"]  # type: ignore[assignment]
    if terms_before or terms_after:
        union = terms_before | terms_after
        overlap = terms_before & terms_after
        parts.append(1.0 - len(overlap) / len(union))
    return round(sum(parts) / len(parts), 6)


def _find_ask(messages: Sequence[ThreadMessage]) -> int | None:
    """Index of the contact's first message that asks for money."""
    for index, message in enumerate(messages):
        if message.sender != "contact":
            continue
        if _MONEY_ASK.search(_fold(message.text)):
            return index
    return None


def _refuses_a_call(messages: Sequence[ThreadMessage]) -> tuple[bool, str]:
    """True when the user proposes a call and the contact deflects it."""
    asked = False
    for message in messages:
        folded = _fold(message.text)
        if message.sender == "user" and _CALL_REQUEST.search(folded):
            asked = True
            continue
        if asked and message.sender == "contact" and _CALL_REFUSAL.search(folded):
            return True, message.text
    return False, ""


def _account_name(text: str) -> str:
    match = _ACCOUNT_NAME.search(_fold(text))
    return match.group(1).strip() if match else ""


def analyze_thread(
    messages: Sequence[ThreadMessage],
    *,
    contact_name: str = "",
    style_shift_threshold: float = STYLE_SHIFT_THRESHOLD,
) -> ThreadAnalysis:
    """Judge a conversation, not a message.

    `contact_name` is the name the user knows this contact by. It never leaves
    the device in raw form; it is only compared against a name written inside
    the thread.
    """
    ask_index = _find_ask(messages)
    contact_indexes = [i for i, m in enumerate(messages) if m.sender == "contact"]

    if ask_index is None:
        return ThreadAnalysis(
            risk="unknown",
            thread_signals=(),
            explanation=(
                "Chưa thấy ai hỏi tiền trong đoạn hội thoại này, nên chưa có gì "
                "để cảnh báo. Đây chưa phải kết luận là an toàn."
            ),
            questions=(),
            baseline_messages=len(contact_indexes),
            style_distance=None,
            ask_message_index=None,
        )

    baseline = [
        messages[i].text for i in contact_indexes if i < ask_index
    ]
    recent = [messages[i].text for i in contact_indexes if i >= ask_index]

    signals: list[ThreadSignal] = []
    distance: float | None = None
    enough_history = len(baseline) >= MIN_BASELINE_MESSAGES

    if enough_history:
        distance = _style_distance(_style_profile(baseline), _style_profile(recent))
        if distance >= style_shift_threshold:
            signals.append(
                ThreadSignal(
                    code="doi_giong_van",
                    confidence=min(1.0, round(distance / style_shift_threshold * 0.6, 4)),
                    evidence=recent[0][:160] if recent else "",
                )
            )
        # Asking for money for the first time only means something when there
        # is a "before" to compare against.
        signals.append(
            ThreadSignal(
                code="yeu_cau_tien_dot_ngot",
                confidence=0.7,
                evidence=messages[ask_index].text[:160],
            )
        )

    refused, refusal_text = _refuses_a_call(messages)
    if refused:
        signals.append(
            ThreadSignal(code="ne_goi_thoai", confidence=0.9, evidence=refusal_text[:160])
        )

    if contact_name:
        written = _account_name(messages[ask_index].text)
        known = _fold(contact_name)
        if written and known and written not in known and known not in written:
            signals.append(
                ThreadSignal(
                    code="tk_khac_ten",
                    confidence=0.85,
                    evidence=messages[ask_index].text[:160],
                )
            )

    ask_folded = _fold(messages[ask_index].text)
    if _URGENCY.search(ask_folded) and _SECRECY.search(ask_folded):
        signals.append(
            ThreadSignal(
                code="gap_va_bi_mat",
                confidence=0.8,
                evidence=messages[ask_index].text[:160],
            )
        )

    found = {signal.code for signal in signals}
    strong = found & {"doi_giong_van", "ne_goi_thoai", "tk_khac_ten"}
    if len(strong) >= 2 or (strong and "gap_va_bi_mat" in found):
        risk = "high"
    elif strong:
        risk = "high" if "tk_khac_ten" in strong else "medium"
    elif "yeu_cau_tien_dot_ngot" in found:
        risk = "medium"
    else:
        risk = "unknown"

    if not enough_history:
        explanation = (
            "Người này mới nhắn quá ít trong đoạn bạn đưa vào, chưa đủ để so "
            "cách nhắn tin trước và sau. Có một lời hỏi tiền — hãy xác minh "
            "bằng cách gọi trực tiếp."
        )
    elif risk == "high":
        explanation = (
            "Cách nhắn tin của người này đã đổi khác so với trước, và lần này "
            "họ hỏi tiền. Đây là dấu hiệu tài khoản bị chiếm quyền. Đừng chuyển "
            "tiền cho tới khi nghe được giọng họ."
        )
    elif risk == "medium":
        explanation = (
            "Đây là lần đầu người này hỏi tiền trong cả đoạn trò chuyện. Chưa "
            "đủ chắc để kết luận, nhưng nên xác minh trước khi chuyển."
        )
    else:
        explanation = (
            "Chưa thấy dấu hiệu bất thường trong đoạn hội thoại này. Đây chưa "
            "phải kết luận là an toàn."
        )

    questions = (
        f"Gọi video cho {contact_name} bằng số cũ để nghe giọng — họ có nghe máy không?"
        if contact_name
        else "Gọi video bằng số cũ của người này để nghe giọng — họ có nghe máy không?",
        "Hỏi một chuyện chỉ hai người biết mà kẻ đọc trộm tin nhắn không thể biết.",
        "Số tài khoản nhận tiền có đúng tên người quen của bạn không?",
    ) if risk in {"high", "medium"} else ()

    return ThreadAnalysis(
        risk=risk,
        thread_signals=tuple(signals),
        explanation=explanation,
        questions=questions,
        baseline_messages=len(baseline),
        style_distance=distance,
        ask_message_index=ask_index,
        insufficient_history=not enough_history,
        detail={"style_shift_threshold": style_shift_threshold},
    )
