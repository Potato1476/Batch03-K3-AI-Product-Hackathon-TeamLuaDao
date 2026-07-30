"""Privacy-preserving FastAPI inference surface for Web and Android."""

from __future__ import annotations

from functools import lru_cache
from typing import cast
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from chan_ml.privacy import RedactionError, redact_l2

from .config import DetectionConfig
from .runtime import ModelRuntime
from .schemas import AnalyzeRequest, AnalyzeResponse, Risk, SignalResult

_ACTIONS: dict[Risk, list[str]] = {
    "high": [
        "report",
        "share_to_guardian",
        "verify_official_channel",
    ],
    "medium": [
        "report",
        "share_to_guardian",
        "verify_official_channel",
    ],
    # Unknown means insufficient evidence, never "safe".
    "unknown": ["verify_if_uncertain"],
}


@lru_cache(maxsize=1)
def get_runtime() -> ModelRuntime:
    try:
        return ModelRuntime.load(DetectionConfig.from_env())
    except (OSError, TypeError, ValueError) as error:
        # Do not return filesystem paths or deserialization details to clients.
        raise HTTPException(
            status_code=503,
            detail="model_unavailable",
        ) from error


def create_app() -> FastAPI:
    application = FastAPI(
        title="CHẮN Detection API",
        version="1.0.0",
        description=(
            "Stateless inference boundary for L2-redacted Vietnamese messages. "
            "Place behind the authenticated, rate-limited API Gateway."
        ),
    )

    @application.exception_handler(RequestValidationError)
    async def safe_validation_error(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        # FastAPI's default validation payload may echo rejected text.
        sanitized = [
            {
                "location": list(item.get("loc", ())),
                "type": item.get("type", "invalid_value"),
            }
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": sanitized})

    @application.middleware("http")
    async def privacy_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.get("/healthz")
    def health(runtime: ModelRuntime = Depends(get_runtime)) -> dict[str, str]:
        return {"status": "ok", "model_version": runtime.model_version}

    @application.post("/v1/analyze", response_model=AnalyzeResponse)
    def analyze(
        payload: AnalyzeRequest,
        runtime: ModelRuntime = Depends(get_runtime),
    ) -> AnalyzeResponse:
        try:
            redacted_text = redact_l2(payload.text)
        except RedactionError as error:
            raise HTTPException(
                status_code=422,
                detail="content_failed_redaction_check",
            ) from error
        prediction = runtime.predict(redacted_text)
        risk = cast(Risk, prediction["risk"])
        actions = list(_ACTIONS[risk])
        if any(
            signal["code"] == "tk_ca_nhan"
            for signal in prediction["signals"]
        ):
            actions.append("lookup_account")
        return AnalyzeResponse(
            analysis_id=f"an_{uuid4().hex[:12]}",
            model_version=runtime.model_version,
            engine_version=str(prediction["engine_version"]),
            risk=risk,
            score=float(prediction["score"]),
            scam_confidence=float(prediction["scam_confidence"]),
            signals=[
                SignalResult(**signal) for signal in prediction["signals"]
            ],
            explanation=str(prediction["explanation"]),
            questions=list(prediction["questions"]),
            actions=actions,
            rule_bundle_version=payload.rule_bundle_version,
            truncated=payload.truncated,
        )

    return application


app = create_app()


def run() -> None:
    # Query/body logging is deliberately disabled at this privacy boundary.
    uvicorn.run(
        "chan_detection.main:app",
        host="0.0.0.0",
        port=8000,
        access_log=False,
    )
