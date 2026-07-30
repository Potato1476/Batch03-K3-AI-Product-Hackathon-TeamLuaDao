"""The OCR seam.

§12 chooses self-hosted PaddleOCR with Cloud Vision as a fallback. Both are heavy
or paid, so the provider is pluggable and the default refuses honestly rather
than pretending to work.
"""

from __future__ import annotations

from typing import Protocol


class OcrError(RuntimeError):
    pass


class OcrUnavailable(OcrError):
    pass


class OcrEngine(Protocol):
    name: str

    async def extract_text(self, image: bytes, *, content_type: str) -> str: ...
