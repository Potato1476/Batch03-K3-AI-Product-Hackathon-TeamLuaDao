"""POST /v1/ocr — screenshot to text (§7).

Returns the text and stops. The client then calls /v1/analyze itself, exactly as
§7 specifies: chaining server-side would create a path where an uploaded image
and its analysis share one request, making the "content lives zero seconds"
guarantee harder to reason about.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import get_rate_limiter
from ..logging_safe import log_event
from ..ocr.base import OcrEngine, OcrError, OcrUnavailable
from ..ocr.layout import lines_to_thread
from ..ratelimit import RateLimiter
from ..schemas import OcrResponse, OcrThreadMessageOut, OcrThreadResponse

router = APIRouter(tags=["ocr"])

_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}

_engine: OcrEngine | None = None
_engine_provider = ""


def _get_engine(config: AppConfig) -> OcrEngine:
    global _engine, _engine_provider
    if _engine is None or _engine_provider != config.ocr_provider:
        if config.ocr_provider == "paddle":
            from ..ocr.paddle import PaddleOcrEngine

            _engine = PaddleOcrEngine()
        elif config.ocr_provider == "tesseract":
            from ..ocr.tesseract import TesseractOcrEngine

            _engine = TesseractOcrEngine(
                language=config.ocr_language,
                timeout_seconds=config.ocr_timeout_seconds,
            )
        else:
            from ..ocr.stub import StubOcrEngine

            _engine = StubOcrEngine()
        _engine_provider = config.ocr_provider
    return _engine


@router.post("/v1/ocr", response_model=OcrResponse)
async def ocr(
    image: UploadFile = File(...),
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> OcrResponse:
    if not limiter.check(
        scope="ocr:device", identity=caller.device_id, limit=10, window_seconds=60
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    if image.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "unsupported_image_type"
        )

    payload = await image.read()
    if not payload:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty_image")
    if len(payload) > config.ocr_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "image_too_large")

    engine = _get_engine(config)
    try:
        text = await engine.extract_text(payload, content_type=image.content_type or "")
    except OcrUnavailable as error:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(error)) from None
    except OcrError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from None
    finally:
        # The bytes are dropped here; nothing writes them anywhere.
        del payload

    log_event("ocr", device_id=caller.device_id, count=len(text))
    return OcrResponse(text=text, provider=engine.name)


@router.post("/v1/ocr/thread", response_model=OcrThreadResponse)
async def ocr_thread(
    image: UploadFile = File(...),
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> OcrThreadResponse:
    """Screenshot of a conversation to an ordered, attributed thread.

    Web users cannot hand CHAN their message history the way the Android client
    can, so the only conversation they can offer is a screenshot. Reading the
    bubble layout recovers who said what; the client then lets the user correct
    it before anything is judged.
    """
    if not limiter.check(
        scope="ocr:device", identity=caller.device_id, limit=10, window_seconds=60
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    if image.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "unsupported_image_type"
        )

    payload = await image.read()
    if not payload:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty_image")
    if len(payload) > config.ocr_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "image_too_large")

    engine = _get_engine(config)
    extract_layout = getattr(engine, "extract_layout", None)
    if extract_layout is None:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED, "ocr_provider_without_layout"
        )
    try:
        lines, width, height = await extract_layout(
            payload, content_type=image.content_type or ""
        )
    except OcrUnavailable as error:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(error)) from None
    except OcrError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from None
    finally:
        del payload

    messages = lines_to_thread(lines, page_width=width, page_height=height)
    if len(messages) < 2:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "ocr_thread_too_short"
        )

    log_event("ocr_thread", device_id=caller.device_id, count=len(messages))
    return OcrThreadResponse(
        messages=[
            OcrThreadMessageOut(sender=message.sender, text=message.text)
            for message in messages
        ],
        provider=engine.name,
    )
