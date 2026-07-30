from __future__ import annotations

import asyncio
import subprocess

import pytest

from chan_api.ocr.base import OcrError, OcrUnavailable
from chan_api.ocr.tesseract import TesseractOcrEngine


def test_tesseract_reads_vietnamese_from_memory(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):  # noqa: ANN001, ANN202
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="Chuyển tiền ngay hôm nay\n".encode(),
            stderr=b"",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    engine = TesseractOcrEngine(language="vie+eng", timeout_seconds=7)

    text = asyncio.run(
        engine.extract_text(b"encoded-image", content_type="image/png")
    )

    assert text == "Chuyển tiền ngay hôm nay"
    assert captured["input"] == b"encoded-image"
    assert captured["command"] == [
        "tesseract",
        "stdin",
        "stdout",
        "-l",
        "vie+eng",
        "--oem",
        "1",
        "--psm",
        "6",
    ]


def test_tesseract_reports_missing_binary(monkeypatch) -> None:
    def missing(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing)
    engine = TesseractOcrEngine()

    with pytest.raises(OcrUnavailable, match="ocr_provider_not_installed"):
        asyncio.run(engine.extract_text(b"image", content_type="image/png"))


def test_tesseract_rejects_an_image_without_text(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(  # noqa: ARG005
            args[0], returncode=0, stdout=b" \n", stderr=b""
        ),
    )
    engine = TesseractOcrEngine()

    with pytest.raises(OcrError, match="ocr_no_text_detected"):
        asyncio.run(engine.extract_text(b"image", content_type="image/jpeg"))
