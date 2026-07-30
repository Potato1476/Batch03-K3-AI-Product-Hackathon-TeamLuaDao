"""The OCR seam.

The provider remains pluggable. Local Docker uses Tesseract because it supports
Vietnamese on both ARM and x86 without a paid API; PaddleOCR remains available
for deployments that provide its larger runtime.
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
