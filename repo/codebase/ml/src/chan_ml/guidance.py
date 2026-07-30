"""Deterministic guidance for messages that lack enough evidence to classify."""

from __future__ import annotations

import re
import unicodedata

from .normalize import normalize_for_model


def _ascii(text: str) -> str:
    normalized = normalize_for_model(text)
    return "".join(
        character
        for character in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")


_GUIDANCE: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"\b(?:(?:toi|em|chau).{0,24}(?:vua|da) bi lua|"
            r"lam sao (?:de )?(?:doi|lay) lai tien)\b"
        ),
        "Nếu bác vừa chuyển tiền do bị lừa, hãy gọi ngay ngân hàng để yêu cầu "
        "chặn giao dịch và trình báo Công an. CHẮN không thể tự lấy lại tiền.",
        "Bác đã gọi ngân hàng để yêu cầu chặn giao dịch chưa?",
    ),
    (
        re.compile(r"\b(?:don hang|goi hang|buu pham).{0,32}(?:su co|chua the giao)\b"),
        "Chưa đủ dữ kiện để kết luận. Bác hãy tự mở ứng dụng mua hàng và kiểm "
        "tra mã vận đơn, không thanh toán qua thông tin trong tin nhắn.",
        "Bác có đơn hàng tương ứng trong ứng dụng chính thức không?",
    ),
    (
        re.compile(r"\b(?:dang nhap|tai khoan).{0,32}(?:bat thuong|co nguoi|co gang)\b"),
        "Đây có thể là cảnh báo thật hoặc giả. Bác hãy tự mở ứng dụng chính "
        "thức để kiểm tra, không bấm liên kết trong tin nhắn.",
        "Tin nhắn có kèm liên kết hoặc yêu cầu cung cấp mã không?",
    ),
    (
        re.compile(r"\b(?:thanh toan|khoan tien).{0,28}(?:xac nhan|cho nhan)\b"),
        "Chưa đủ dữ kiện để kết luận. Bác hãy kiểm tra trực tiếp trong ứng "
        "dụng ngân hàng và không chuyển phí để nhận tiền.",
        "Khoản tiền này có xuất hiện trong ứng dụng ngân hàng của bác không?",
    ),
    (
        re.compile(r"\b(?:ho so|xac minh danh tinh|cap nhat thong tin)\b"),
        "Nhiều đơn vị thật cũng có thể yêu cầu việc này. Bác chỉ nên kiểm tra "
        "qua ứng dụng, website hoặc số điện thoại chính thức tự tìm được.",
        "Đơn vị nào gửi tin và họ yêu cầu cung cấp thông tin gì?",
    ),
    (
        re.compile(r"\b(?:phan qua|trung thuong|qua dac biet)\b"),
        "Chưa đủ dữ kiện để kết luận. Nếu họ yêu cầu nộp phí, chuyển tiền hoặc "
        "đọc mã xác nhận để nhận quà thì hãy dừng lại.",
        "Bác có đăng ký chương trình này và họ có yêu cầu nộp phí không?",
    ),
    (
        re.compile(r"\b(?:co quan chuc nang|vi pham quy dinh)\b"),
        "Chưa đủ dữ kiện để kết luận. Bác không nên làm theo ngay; hãy tự gọi "
        "số công khai của cơ quan để xác minh.",
        "Tin nhắn nêu rõ cơ quan, hồ sơ và kênh xác minh chính thức không?",
    ),
    (
        re.compile(r"\b(?:cuoc hen|lich hen).{0,20}(?:ngay mai|sap toi)\b"),
        "Tin nhắn chưa nêu rõ đơn vị và nội dung cuộc hẹn.",
        "Bác có lịch hẹn tương ứng và biết rõ đơn vị gửi không?",
    ),
)


def guidance_for_unknown(text: str) -> tuple[str, list[str]]:
    normalized = _ascii(text)
    for pattern, explanation, question in _GUIDANCE:
        if pattern.search(normalized):
            return explanation, [question]
    return (
        "Chưa đủ thông tin để kết luận là an toàn hay lừa đảo.",
        [
            "Tin nhắn đến từ đâu và có yêu cầu bấm link, chuyển tiền hoặc "
            "cung cấp mã xác nhận không?"
        ],
    )


def is_victim_recovery_request(text: str) -> bool:
    normalized = _ascii(text)
    return bool(_GUIDANCE[0][0].search(normalized))
