"""Default OCR provider: declares itself unavailable.

Returning empty text would be worse than an error: the client would call
/v1/analyze with nothing, get `unknown`, and show the user "Chưa phát hiện dấu
hiệu" for a screenshot that was never read. A refusal the client can display is
the honest outcome.
"""

from __future__ import annotations

from .base import OcrUnavailable


class StubOcrEngine:
    name = "stub"

    async def extract_text(self, image: bytes, *, content_type: str) -> str:
        raise OcrUnavailable("ocr_provider_not_configured")
