"""PostgreSQL repository with no content-bearing log statements."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

import psycopg
from fastapi import Depends
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from chan_ml.normalize import normalize_for_model

from .config import AppConfig, get_config
from .schemas import ScenarioSubmission


@dataclass(frozen=True)
class ScenarioReceiptRecord:
    id: str
    status: str
    duplicate: bool


@dataclass(frozen=True)
class ApprovedScenario:
    id: str
    redacted_text: str
    signals: tuple[str, ...]
    risk: str
    is_phishing: bool
    origin: str
    rights_basis: str
    consented: bool


@dataclass(frozen=True)
class TrainingRun:
    id: str
    status: str
    submitted_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    approved_scenario_count: int | None
    candidate_version: str | None
    metrics: dict[str, object] | None
    promotion_reasons: tuple[str, ...]
    error_code: str | None


@dataclass(frozen=True)
class ActiveModel:
    version: str
    artifact_uri: str
    artifact_sha256: str
    metrics: dict[str, object]
    promoted_at: datetime


class TrainingRepository(Protocol):
    def submit_scenarios(
        self, items: Sequence[ScenarioSubmission], actor: str
    ) -> list[ScenarioReceiptRecord]: ...

    def review_scenario(
        self, scenario_id: str, decision: str, reason: str, actor: str
    ) -> str | None: ...

    def queue_training(self, idempotency_key: str, actor: str) -> TrainingRun: ...

    def get_training_run(self, run_id: str) -> TrainingRun | None: ...

    def get_active_model(self) -> ActiveModel | None: ...

    def claim_training_run(self) -> TrainingRun | None: ...

    def list_approved_scenarios(self) -> list[ApprovedScenario]: ...

    def complete_training_run(
        self,
        *,
        run_id: str,
        candidate_version: str,
        artifact_uri: str,
        artifact_sha256: str,
        metrics: dict[str, object],
        approved_scenario_count: int,
        promote: bool,
        reasons: Sequence[str],
    ) -> None: ...

    def fail_training_run(self, run_id: str, error_code: str) -> None: ...

    def expire_quarantine(self, retention_days: int = 7) -> int: ...


def _training_run(row: dict[str, object]) -> TrainingRun:
    raw_reasons = row.get("promotion_reasons")
    promotion_reasons = (
        tuple(str(item) for item in raw_reasons)
        if isinstance(raw_reasons, (list, tuple))
        else ()
    )
    return TrainingRun(
        id=str(row["id"]),
        status=str(row["status"]),
        submitted_at=row["submitted_at"],  # type: ignore[arg-type]
        started_at=row.get("started_at"),  # type: ignore[arg-type]
        finished_at=row.get("finished_at"),  # type: ignore[arg-type]
        approved_scenario_count=row.get("approved_scenario_count"),  # type: ignore[arg-type]
        candidate_version=row.get("candidate_version"),  # type: ignore[arg-type]
        metrics=row.get("metrics"),  # type: ignore[arg-type]
        promotion_reasons=promotion_reasons,
        error_code=row.get("error_code"),  # type: ignore[arg-type]
    )


class PostgresTrainingRepository:
    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("CHAN_DATABASE_URL is required")
        self.dsn = dsn

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def submit_scenarios(
        self, items: Sequence[ScenarioSubmission], actor: str
    ) -> list[ScenarioReceiptRecord]:
        receipts: list[ScenarioReceiptRecord] = []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for item in items:
                    scenario_id = uuid.uuid4()
                    normalized = normalize_for_model(item.redacted_text)
                    text_hash = hashlib.sha256(normalized.encode("utf-8")).digest()
                    source_hash = (
                        hashlib.sha256(item.source_ref.encode("utf-8")).digest()
                        if item.source_ref
                        else None
                    )
                    cursor.execute(
                        """
                        INSERT INTO training_scenarios (
                            id, redacted_text, text_sha256, signals, risk,
                            is_phishing, origin, source_ref_hash, rights_basis,
                            consented, redaction_confirmed, submitted_by
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s
                        )
                        ON CONFLICT (text_sha256) DO NOTHING
                        RETURNING id, status
                        """,
                        (
                            scenario_id,
                            item.redacted_text,
                            text_hash,
                            list(item.signals),
                            item.risk,
                            item.is_phishing,
                            item.origin,
                            source_hash,
                            item.rights_basis,
                            item.consented,
                            actor,
                        ),
                    )
                    inserted = cursor.fetchone()
                    if inserted:
                        cursor.execute(
                            """
                            INSERT INTO training_scenario_audit (
                                scenario_id, action, actor
                            ) VALUES (%s, 'submitted', %s)
                            """,
                            (scenario_id, actor),
                        )
                        receipts.append(
                            ScenarioReceiptRecord(
                                id=str(inserted["id"]),
                                status=str(inserted["status"]),
                                duplicate=False,
                            )
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT id, status
                            FROM training_scenarios
                            WHERE text_sha256 = %s
                            """,
                            (text_hash,),
                        )
                        existing = cursor.fetchone()
                        if existing is None:
                            raise RuntimeError("scenario_deduplication_failed")
                        receipts.append(
                            ScenarioReceiptRecord(
                                id=str(existing["id"]),
                                status=str(existing["status"]),
                                duplicate=True,
                            )
                        )
        return receipts

    def review_scenario(
        self, scenario_id: str, decision: str, reason: str, actor: str
    ) -> str | None:
        target_status = "approved" if decision == "approve" else "rejected"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE training_scenarios
                    SET status = %s,
                        redacted_text = CASE
                            WHEN %s = 'rejected' THEN NULL
                            ELSE redacted_text
                        END,
                        reviewed_by = %s,
                        reviewed_at = now(),
                        review_reason = %s
                    WHERE id = %s
                      AND status = 'quarantined'
                      AND submitted_by <> %s
                    RETURNING status
                    """,
                    (
                        target_status,
                        target_status,
                        actor,
                        reason,
                        scenario_id,
                        actor,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute(
                    """
                    INSERT INTO training_scenario_audit (
                        scenario_id, action, actor, reason_code
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (scenario_id, target_status, actor, reason),
                )
                return str(row["status"])

    def queue_training(self, idempotency_key: str, actor: str) -> TrainingRun:
        run_id = uuid.uuid4()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO training_runs (
                        id, idempotency_key, submitted_by
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING *
                    """,
                    (run_id, idempotency_key, actor),
                )
                row = cursor.fetchone()
                if row is None:
                    cursor.execute(
                        "SELECT * FROM training_runs WHERE idempotency_key = %s",
                        (idempotency_key,),
                    )
                    row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("training_queue_failed")
                return _training_run(row)

    def get_training_run(self, run_id: str) -> TrainingRun | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM training_runs WHERE id = %s", (run_id,))
                row = cursor.fetchone()
                return _training_run(row) if row else None

    def get_active_model(self) -> ActiveModel | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT version, artifact_uri, artifact_sha256,
                           metrics, promoted_at
                    FROM model_versions
                    WHERE status = 'active'
                    """
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return ActiveModel(
                    version=str(row["version"]),
                    artifact_uri=str(row["artifact_uri"]),
                    artifact_sha256=str(row["artifact_sha256"]),
                    metrics=row["metrics"],  # type: ignore[arg-type]
                    promoted_at=row["promoted_at"],  # type: ignore[arg-type]
                )

    def claim_training_run(self) -> TrainingRun | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id FROM training_runs
                    WHERE status = 'queued'
                    ORDER BY submitted_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                )
                queued = cursor.fetchone()
                if queued is None:
                    return None
                cursor.execute(
                    """
                    UPDATE training_runs
                    SET status = 'running', started_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (queued["id"],),
                )
                row = cursor.fetchone()
                return _training_run(row) if row else None

    def list_approved_scenarios(self) -> list[ApprovedScenario]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, redacted_text, signals, risk, is_phishing,
                           origin, rights_basis, consented
                    FROM training_scenarios
                    WHERE status = 'approved'
                    ORDER BY submitted_at
                    """
                )
                return [
                    ApprovedScenario(
                        id=str(row["id"]),
                        redacted_text=str(row["redacted_text"]),
                        signals=tuple(row["signals"]),
                        risk=str(row["risk"]),
                        is_phishing=bool(row["is_phishing"]),
                        origin=str(row["origin"]),
                        rights_basis=str(row["rights_basis"]),
                        consented=bool(row["consented"]),
                    )
                    for row in cursor.fetchall()
                ]

    def complete_training_run(
        self,
        *,
        run_id: str,
        candidate_version: str,
        artifact_uri: str,
        artifact_sha256: str,
        metrics: dict[str, object],
        approved_scenario_count: int,
        promote: bool,
        reasons: Sequence[str],
    ) -> None:
        model_status = "active" if promote else "rejected"
        run_status = "promoted" if promote else "rejected"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if promote:
                    cursor.execute(
                        """
                        UPDATE model_versions
                        SET status = 'archived'
                        WHERE status = 'active'
                        """
                    )
                cursor.execute(
                    """
                    INSERT INTO model_versions (
                        version, artifact_uri, artifact_sha256, metrics,
                        status, training_run_id, promoted_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        CASE WHEN %s THEN now() ELSE NULL END
                    )
                    """,
                    (
                        candidate_version,
                        artifact_uri,
                        artifact_sha256,
                        Jsonb(metrics),
                        model_status,
                        run_id,
                        promote,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE training_runs
                    SET status = %s,
                        finished_at = now(),
                        approved_scenario_count = %s,
                        candidate_version = %s,
                        metrics = %s,
                        promotion_reasons = %s
                    WHERE id = %s AND status = 'running'
                    """,
                    (
                        run_status,
                        approved_scenario_count,
                        candidate_version,
                        Jsonb(metrics),
                        list(reasons),
                        run_id,
                    ),
                )

    def fail_training_run(self, run_id: str, error_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE training_runs
                SET status = 'failed', finished_at = now(), error_code = %s
                WHERE id = %s AND status = 'running'
                """,
                (error_code[:128], run_id),
            )

    def expire_quarantine(self, retention_days: int = 7) -> int:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE training_scenarios
                    SET status = 'expired', redacted_text = NULL
                    WHERE status = 'quarantined'
                      AND submitted_at < now() - (%s * interval '1 day')
                    RETURNING id
                    """,
                    (retention_days,),
                )
                expired = cursor.fetchall()
                if expired:
                    cursor.executemany(
                        """
                        INSERT INTO training_scenario_audit (
                            scenario_id, action, actor, reason_code
                        ) VALUES (%s, 'expired', 'system', 'quarantine_ttl')
                        """,
                        [(row["id"],) for row in expired],
                    )
                return len(expired)


def get_repository(
    config: AppConfig = Depends(get_config),
) -> PostgresTrainingRepository:
    return PostgresTrainingRepository(config.database_url)
