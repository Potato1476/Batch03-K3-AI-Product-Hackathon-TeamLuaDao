"""Privacy-preserving FastAPI inference surface for Web and Android."""

from __future__ import annotations

from functools import lru_cache
from typing import cast
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from chan_ml.redact import RedactionError, redact_l2
from chan_ml.thread import (
    THREAD_SIGNAL_LABELS,
    ThreadMessage,
    analyze_thread,
)

from .config import DetectionConfig
from .intel import IntelLookupClient
from .runtime import ModelPrediction, ModelRuntime, RuntimeProvider
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeThreadRequest,
    AnalyzeThreadResponse,
    Risk,
    SignalResult,
    ThreadSignalResult,
)
from .security import require_gateway

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
def get_runtime_provider() -> RuntimeProvider:
    return RuntimeProvider(DetectionConfig.from_env())


def get_runtime() -> ModelRuntime:
    try:
        return get_runtime_provider().current()
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        # Do not return filesystem paths or deserialization details to clients.
        raise HTTPException(
            status_code=503,
            detail="model_unavailable",
        ) from error


@lru_cache(maxsize=1)
def get_intel_client() -> IntelLookupClient:
    return IntelLookupClient(DetectionConfig.from_env())


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

    @application.post("/internal/v1/analyze", response_model=AnalyzeResponse)
    def analyze(
        payload: AnalyzeRequest,
        _gateway: None = Depends(require_gateway),
        runtime: ModelRuntime = Depends(get_runtime),
        intel: IntelLookupClient = Depends(get_intel_client),
    ) -> AnalyzeResponse:
        try:
            redaction = redact_l2(payload.text)
        except RedactionError as error:
            raise HTTPException(
                status_code=422,
                detail="content_failed_redaction_check",
            ) from error
        blocklist_match = intel.contains(redaction)
        if redaction.otp_found:
            prediction: ModelPrediction = {
                "risk": "high",
                "score": 1.0,
                "scam_confidence": 1.0,
                "signals": [
                    {
                        "code": "yeu_cau_otp",
                        "confidence": 1.0,
                        "evidence": "",
                    }
                ],
                "explanation": (
                    "Tin nhắn này đang hỏi mã xác nhận của bạn. "
                    "Đừng đọc mã cho bất kỳ ai."
                ),
                "questions": ["Tại sao họ cần mã xác nhận của tôi?"],
                "engine_version": runtime.model_version,
            }
        else:
            prediction = (
                runtime.predict(
                    redaction.text,
                    signal_boosts=payload.local_boosts,
                    verified_local_signals=tuple(payload.local_signals),
                )
                if payload.local_boosts or payload.local_signals
                else runtime.predict(redaction.text)
            )
        if blocklist_match:
            prediction = {
                **prediction,
                "risk": "high",
                "score": 1.0,
                "explanation": (
                    "Số nhận tiền hoặc liên kết này đã bị người khác "
                    "báo cáo là lừa đảo. Đừng tiếp tục giao dịch."
                ),
            }
        risk = cast(Risk, prediction["risk"])
        actions = list(_ACTIONS[risk])
        if any(
            signal["code"] == "tk_ca_nhan"
            for signal in prediction["signals"]
        ):
            actions.append("lookup_account")
        if blocklist_match and "lookup_account" not in actions:
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
            blocklist_match=blocklist_match,
        )

    @application.post(
        "/internal/v1/analyze-thread", response_model=AnalyzeThreadResponse
    )
    def analyze_conversation(
        payload: AnalyzeThreadRequest,
        _gateway: None = Depends(require_gateway),
        runtime: ModelRuntime = Depends(get_runtime),
    ) -> AnalyzeThreadResponse:
        """L5: judge a conversation against the contact's own past.

        A hijacked account writes one message that a real friend could also
        write. The decision therefore has to be made across turns, on features
        that survive impersonation: how this person types, whether they have
        ever asked for money here, and whether they will take a call.
        """
        messages = [
            ThreadMessage(sender=item.sender, text=item.text)
            for item in payload.messages
        ]
        thread = analyze_thread(messages, contact_name=payload.contact_name)

        # The message that asked for money still goes through the eight-signal
        # model, so a thread that is *also* a classic scam picks up both.
        ask_risk: Risk | None = None
        ask_signals: list[SignalResult] = []
        if thread.ask_message_index is not None:
            try:
                redaction = redact_l2(messages[thread.ask_message_index].text)
            except RedactionError as error:
                raise HTTPException(
                    status_code=422,
                    detail="content_failed_redaction_check",
                ) from error
            if redaction.otp_found:
                ask_risk = "high"
                ask_signals = [
                    SignalResult(code="yeu_cau_otp", confidence=1.0, evidence="")
                ]
            else:
                prediction = runtime.predict(redaction.text)
                ask_risk = cast(Risk, prediction["risk"])
                ask_signals = [
                    SignalResult(**signal) for signal in prediction["signals"]
                ]

        risk = cast(Risk, thread.risk)
        # A thread never talks its way down out of a per-message verdict.
        if ask_risk == "high" or (ask_risk == "medium" and risk == "unknown"):
            risk = ask_risk
        return AnalyzeThreadResponse(
            analysis_id=f"th_{uuid4().hex[:12]}",
            risk=risk,
            thread_signals=[
                ThreadSignalResult(
                    code=signal.code,
                    label=THREAD_SIGNAL_LABELS.get(signal.code, signal.code),
                    confidence=signal.confidence,
                    evidence=signal.evidence,
                )
                for signal in thread.thread_signals
            ],
            explanation=thread.explanation,
            questions=list(thread.questions),
            actions=list(_ACTIONS[risk]),
            baseline_messages=thread.baseline_messages,
            style_distance=thread.style_distance,
            insufficient_history=thread.insufficient_history,
            ask_message_index=thread.ask_message_index,
            ask_message_risk=ask_risk,
            ask_message_signals=ask_signals,
            engine_version=runtime.model_version,
            rule_bundle_version=payload.rule_bundle_version,
        )

    return application


app = create_app()


def run() -> None:
    # Query/body logging is deliberately disabled at this privacy boundary.
    uvicorn.run(
        "chan_detection.main:app",
        host="0.0.0.0",
        port=8003,
        access_log=False,
    )
