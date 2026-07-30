"""Private FastAPI surface for reviewed scenario ingestion and retraining."""

from __future__ import annotations

from typing import cast
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .repository import TrainingRepository, get_repository
from .schemas import (
    ActiveModelResponse,
    RetrainRequest,
    ReviewRequest,
    ReviewResponse,
    ScenarioBatchRequest,
    ScenarioBatchResponse,
    ScenarioReceipt,
    ScenarioStatus,
    TrainingRunResponse,
)
from .security import require_training_actor


def _run_response(run) -> TrainingRunResponse:
    return TrainingRunResponse(
        id=run.id,
        status=run.status,
        submitted_at=run.submitted_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        approved_scenario_count=run.approved_scenario_count,
        candidate_version=run.candidate_version,
        metrics=run.metrics,
        promotion_reasons=list(run.promotion_reasons),
        error_code=run.error_code,
    )


def create_app() -> FastAPI:
    application = FastAPI(
        title="CHẮN Private Training API",
        version="0.1.0",
        description=(
            "Internal-only ingestion, review, retraining, and model registry. "
            "Never expose this service directly to end-user clients."
        ),
    )

    @application.exception_handler(RequestValidationError)
    async def safe_validation_error(_request, error: RequestValidationError):
        # FastAPI's default response can echo rejected input. Return locations
        # and error types only so message text never appears in a response/log.
        sanitized = [
            {
                "location": list(item.get("loc", ())),
                "type": item.get("type", "invalid_value"),
            }
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": sanitized},
        )

    @application.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/internal/v1/training/scenarios",
        response_model=ScenarioBatchResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def submit_scenarios(
        payload: ScenarioBatchRequest,
        actor: str = Depends(require_training_actor),
        repository: TrainingRepository = Depends(get_repository),
    ) -> ScenarioBatchResponse:
        receipts = repository.submit_scenarios(payload.items, actor)
        return ScenarioBatchResponse(
            accepted=len(receipts),
            items=[
                ScenarioReceipt(
                    id=item.id,
                    status=cast(ScenarioStatus, item.status),
                    duplicate=item.duplicate,
                )
                for item in receipts
            ],
        )

    @application.post(
        "/internal/v1/training/scenarios/{scenario_id}/review",
        response_model=ReviewResponse,
    )
    def review_scenario(
        scenario_id: UUID,
        payload: ReviewRequest,
        actor: str = Depends(require_training_actor),
        repository: TrainingRepository = Depends(get_repository),
    ) -> ReviewResponse:
        result = repository.review_scenario(
            str(scenario_id), payload.decision, payload.review_reason, actor
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="quarantined_scenario_not_found",
            )
        return ReviewResponse(
            id=str(scenario_id), status=cast(ScenarioStatus, result)
        )

    @application.post(
        "/internal/v1/training/retrain",
        response_model=TrainingRunResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def queue_retraining(
        payload: RetrainRequest,
        actor: str = Depends(require_training_actor),
        repository: TrainingRepository = Depends(get_repository),
    ) -> TrainingRunResponse:
        return _run_response(
            repository.queue_training(payload.idempotency_key, actor)
        )

    @application.get(
        "/internal/v1/training/runs/{run_id}",
        response_model=TrainingRunResponse,
    )
    def get_run(
        run_id: UUID,
        _actor: str = Depends(require_training_actor),
        repository: TrainingRepository = Depends(get_repository),
    ) -> TrainingRunResponse:
        run = repository.get_training_run(str(run_id))
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="training_run_not_found",
            )
        return _run_response(run)

    @application.get(
        "/internal/v1/training/models/active",
        response_model=ActiveModelResponse,
    )
    def get_active_model(
        _actor: str = Depends(require_training_actor),
        repository: TrainingRepository = Depends(get_repository),
    ) -> ActiveModelResponse:
        model = repository.get_active_model()
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="active_model_not_found",
            )
        return ActiveModelResponse(
            version=model.version,
            artifact_uri=model.artifact_uri,
            artifact_sha256=model.artifact_sha256,
            metrics=model.metrics,
            promoted_at=model.promoted_at,
        )
    return application


app = create_app()


def run() -> None:
    # Access logs include paths only, but disabling them further reduces the
    # chance of future middleware accidentally logging query/body content.
    uvicorn.run(
        "chan_training_api.main:app",
        host="0.0.0.0",
        port=8001,
        access_log=False,
    )


if __name__ == "__main__":
    run()
