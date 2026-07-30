"""FastAPI surface for k-anonymous lookup and internal intel operations."""

from __future__ import annotations

from typing import cast
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import IntelConfig, get_config
from .repository import IntelRepository, get_repository
from .schemas import (
    Confidence,
    IndicatorKind,
    IndicatorReportBatchRequest,
    IndicatorReportBatchResponse,
    IndicatorReportReceipt,
    LookupItem,
    LookupResponse,
    ReportStatus,
    ReviewRequest,
    ReviewResponse,
    SourceStatusResponse,
)
from .security import require_intel_actor


def create_app() -> FastAPI:
    application = FastAPI(
        title="CHẮN Threat Intel & Lookup API",
        version="0.1.0",
        description=(
            "Hash-only blocklists, k-anonymous lookup, licensed feed status, "
            "and quarantined community reports."
        ),
    )

    @application.exception_handler(RequestValidationError)
    async def safe_validation_error(_request, error: RequestValidationError):
        sanitized = [
            {
                "location": list(item.get("loc", ())),
                "type": item.get("type", "invalid_value"),
            }
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": sanitized})

    @application.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get(
        "/v1/lookup/{kind}",
        response_model=LookupResponse,
    )
    def lookup(
        kind: IndicatorKind,
        prefix: str = Query(
            min_length=2, max_length=5, pattern=r"^[0-9a-f]{2,5}$"
        ),
        repository: IntelRepository = Depends(get_repository),
        config: IntelConfig = Depends(get_config),
    ) -> LookupResponse:
        if len(prefix) != config.lookup_prefix_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="lookup_prefix_length_mismatch",
            )
        records = repository.lookup(kind, prefix)
        return LookupResponse(
            prefix=prefix,
            items=[
                LookupItem(
                    suffix=item.digest_hex[len(prefix) :],
                    report_count=item.report_count,
                    first_seen=item.first_seen,
                    last_seen=item.last_seen,
                    confidence=cast(Confidence, item.confidence),
                )
                for item in records
            ],
        )

    @application.post(
        "/internal/v1/intel/reports",
        response_model=IndicatorReportBatchResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def submit_reports(
        payload: IndicatorReportBatchRequest,
        actor: str = Depends(require_intel_actor),
        repository: IntelRepository = Depends(get_repository),
    ) -> IndicatorReportBatchResponse:
        receipts = repository.submit_reports(payload.items, actor)
        return IndicatorReportBatchResponse(
            accepted=len(receipts),
            items=[
                IndicatorReportReceipt(
                    id=item.id,
                    status=cast(ReportStatus, item.status),
                    duplicate=item.duplicate,
                )
                for item in receipts
            ],
        )

    @application.post(
        "/internal/v1/intel/reports/{report_id}/review",
        response_model=ReviewResponse,
    )
    def review_report(
        report_id: UUID,
        payload: ReviewRequest,
        actor: str = Depends(require_intel_actor),
        repository: IntelRepository = Depends(get_repository),
        config: IntelConfig = Depends(get_config),
    ) -> ReviewResponse:
        result = repository.review_report(
            str(report_id),
            payload.decision,
            payload.review_reason,
            actor,
            config.user_report_threshold,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="quarantined_report_not_found",
            )
        report_status, count, activated = result
        return ReviewResponse(
            id=str(report_id),
            status=cast(ReportStatus, report_status),
            independent_approved_reports=count,
            activated=activated,
        )

    @application.get(
        "/internal/v1/intel/sources",
        response_model=list[SourceStatusResponse],
    )
    def sources(
        _actor: str = Depends(require_intel_actor),
        repository: IntelRepository = Depends(get_repository),
    ) -> list[SourceStatusResponse]:
        return [
            SourceStatusResponse(
                name=item.name,
                enabled=item.enabled,
                rights_basis=item.rights_basis,
                update_interval_minutes=item.update_interval_minutes,
                last_success_at=item.last_success_at,
                last_record_count=item.last_record_count,
                last_error_code=item.last_error_code,
            )
            for item in repository.list_sources()
        ]

    return application


app = create_app()


def run() -> None:
    # Prefixes are query parameters. Disable access logs so they cannot leak
    # into infrastructure logs; the gateway should log only route and status.
    uvicorn.run(
        "chan_intel.main:app",
        host="0.0.0.0",
        port=8002,
        access_log=False,
    )


if __name__ == "__main__":
    run()
