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


class LayoutOcrEngine(OcrEngine, Protocol):
    """An engine that also reports where on the page each line was found.

    Chat screenshots keep who-said-what in the layout, so an engine without
    this capability cannot serve /v1/ocr/thread.
    """

    async def extract_layout(
        self, image: bytes, *, content_type: str
    ) -> tuple[list, int, int]: ...
