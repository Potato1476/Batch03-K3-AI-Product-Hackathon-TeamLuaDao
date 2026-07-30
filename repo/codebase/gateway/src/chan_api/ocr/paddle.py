"""PaddleOCR provider — Vietnamese with diacritics, self-hosted, no per-call cost.

Imported lazily and installed only via the `[ocr]` extra: paddlepaddle is a very
large dependency and must not be required to run or test the rest of the service.

The image is decoded in memory and never written to disk (§7.2: message content
lives zero seconds server-side).
"""

from __future__ import annotations

import threading

from starlette.concurrency import run_in_threadpool

from .base import OcrError


class PaddleOcrEngine:
    name = "paddle"

    def __init__(self, *, lang: str = "vi") -> None:
        self._lang = lang
        self._lock = threading.Lock()
        self._reader = None

    def _ensure_reader(self):  # noqa: ANN202
        with self._lock:
            if self._reader is None:
                try:
                    from paddleocr import PaddleOCR
                except ImportError as error:  # pragma: no cover
                    raise OcrError("ocr_provider_not_installed") from error
                self._reader = PaddleOCR(use_angle_cls=True, lang=self._lang, show_log=False)
            return self._reader

    async def extract_text(self, image: bytes, *, content_type: str) -> str:
        return await run_in_threadpool(self._extract_sync, image)

    def _extract_sync(self, image: bytes) -> str:
        import numpy as np

        try:
            import cv2

            array = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        except ImportError:  # pragma: no cover - cv2 ships with paddleocr
            from io import BytesIO

            from PIL import Image

            array = np.array(Image.open(BytesIO(image)).convert("RGB"))
        if array is None:
            raise OcrError("ocr_unreadable_image")

        reader = self._ensure_reader()
        try:
            result = reader.ocr(array, cls=True)
        except Exception as error:  # noqa: BLE001 - never surface provider text
            raise OcrError(type(error).__name__) from None

        lines: list[str] = []
        for page in result or []:
            for entry in page or []:
                # PaddleOCR returns [box, (text, confidence)] per line.
                if len(entry) >= 2 and isinstance(entry[1], (list, tuple)):
                    text = str(entry[1][0]).strip()
                    if text:
                        lines.append(text)
        return "\n".join(lines)
