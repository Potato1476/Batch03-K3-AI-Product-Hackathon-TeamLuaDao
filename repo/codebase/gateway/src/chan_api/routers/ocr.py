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
from ..ratelimit import RateLimiter
from ..schemas import OcrResponse

router = APIRouter(tags=["ocr"])

_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}

_engine: OcrEngine | None = None


def _get_engine(config: AppConfig):  # noqa: ANN202
    global _engine
    if _engine is None:
        if config.ocr_provider == "paddle":
            from ..ocr.paddle import PaddleOcrEngine

            _engine = PaddleOcrEngine()
        else:
            from ..ocr.stub import StubOcrEngine

            _engine = StubOcrEngine()
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
