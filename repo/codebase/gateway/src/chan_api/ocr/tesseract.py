"""Offline Vietnamese OCR backed by the Tesseract command-line engine.

The encoded image is piped through stdin and recognized text is read from
stdout. No temporary image file is created by CHAN, so request content remains
ephemeral at the Gateway boundary.
"""

from __future__ import annotations

import os
import subprocess

from starlette.concurrency import run_in_threadpool

from .base import OcrError, OcrUnavailable
from .layout import OcrLine, parse_tesseract_tsv


class TesseractOcrEngine:
    name = "tesseract"

    def __init__(self, *, language: str = "vie+eng", timeout_seconds: float = 20.0) -> None:
        self._language = language
        self._timeout_seconds = timeout_seconds

    async def extract_text(self, image: bytes, *, content_type: str) -> str:
        del content_type
        return await run_in_threadpool(self._extract_sync, image)

    async def extract_layout(
        self, image: bytes, *, content_type: str
    ) -> tuple[list[OcrLine], int, int]:
        """Same recognition, but keep the box each line was found in."""
        del content_type
        return await run_in_threadpool(self._extract_layout_sync, image)

    def _extract_layout_sync(self, image: bytes) -> tuple[list[OcrLine], int, int]:
        raw = self._run(image, extra=("tsv",)).decode("utf-8", errors="replace")
        lines, width, height = parse_tesseract_tsv(raw)
        if not lines:
            raise OcrError("ocr_no_text_detected")
        return lines, width, height

    def _extract_sync(self, image: bytes) -> str:
        stdout = self._run(image)
        text = "\n".join(
            line.strip()
            for line in stdout.decode("utf-8", errors="replace").splitlines()
            if line.strip()
        )
        if not text:
            raise OcrError("ocr_no_text_detected")
        return text

    def _run(self, image: bytes, *, extra: tuple[str, ...] = ()) -> bytes:
        command = [
            "tesseract",
            "stdin",
            "stdout",
            "-l",
            self._language,
            "--oem",
            "1",
            "--psm",
            "6",
            *extra,
        ]
        environment = {**os.environ, "OMP_THREAD_LIMIT": "2"}
        try:
            result = subprocess.run(  # noqa: S603 - fixed executable and arguments
                command,
                input=image,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=self._timeout_seconds,
                env=environment,
            )
        except FileNotFoundError as error:
            raise OcrUnavailable("ocr_provider_not_installed") from error
        except subprocess.TimeoutExpired as error:
            raise OcrError("ocr_timeout") from error
        if result.returncode != 0:
            raise OcrError("ocr_engine_failed")
        return result.stdout
