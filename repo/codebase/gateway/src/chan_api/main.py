"""The public CHẮN /v1 service.

Runs on port 8000 and is separate from the private training control plane on
8001 — see codebase/training_api. A single process serving both would put the quarantine
and retrain endpoints one routing mistake away from the internet.
"""

from __future__ import annotations

import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import AppConfig, get_config
from .deps import get_detection_client
from .service_clients import DetectionClient
from .logging_safe import configure_logging, log_error, log_event
from .routers import analyze, devices, feedback, lookup, ocr, report, rules

_TITLE = "CHẮN Public API"
_VERSION = "0.1.0"


def create_app(
    config: AppConfig | None = None, *, poll_model: bool = True
) -> FastAPI:
    config = config or get_config()
    configure_logging()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Kept as a lifespan hook for future client cleanup. Model lifecycle is
        # owned by Detection, never by the public gateway.
        yield

    app = FastAPI(
        title=_TITLE,
        version=_VERSION,
        lifespan=lifespan,
        description=(
            "Hợp đồng API dùng chung cho Web PWA, Android và Zalo OA. "
            "Không có nhãn 'An toàn' — chỉ high / medium / unknown."
        ),
    )

    if config.cors_origins:
        # The PWA is a separate origin; Android and the Zalo webhook are not
        # browsers and need none of this.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "If-None-Match"],
            max_age=600,
        )

    @app.middleware("http")
    async def observe(request: Request, call_next):  # noqa: ANN001, ANN202
        request_id = secrets.token_hex(8)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log_error(
                "request_failed",
                "unhandled_exception",
                request_id=request_id,
                endpoint=request.url.path,
                method=request.method,
                status=500,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            raise
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-Id"] = request_id
        # Path only — never the query string, which carries lookup prefixes (I4).
        log_event(
            "request",
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            status=response.status_code,
            latency_ms=latency_ms,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):  # noqa: ANN202
        # Same treatment as the training API: report where the problem is and
        # what kind it was, never the value. A rejected payload may contain an
        # OTP, and an echoed error message is a leak.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": [
                    {"location": list(item.get("loc", ())), "type": item.get("type", "")}
                    for item in error.errors()
                ]
            },
        )

    @app.get("/healthz", tags=["ops"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["ops"])
    async def readyz(
        detection: DetectionClient = Depends(get_detection_client),
    ) -> JSONResponse:
        """Ready means the delegated Detection service is reachable."""
        ready = await detection.healthy()
        return JSONResponse(
            status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "ready" if ready else "detection_unavailable",
            },
        )

    for module in (devices, analyze, ocr, lookup, report, rules, feedback):
        app.include_router(module.router)

    return app

app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "chan_api.main:app",
        host="0.0.0.0",
        # 8000 is the public edge. 8001 belongs to the private training API, and
        # binding it here made `chan-gateway` fail to start whenever the control
        # plane was already running.
        port=int(os.environ.get("CHAN_GATEWAY_PORT", "8000")),
        # Access logging is handled by the safe logger; uvicorn's own access log
        # would print the query string, which carries lookup prefixes (I4).
        access_log=False,
    )
