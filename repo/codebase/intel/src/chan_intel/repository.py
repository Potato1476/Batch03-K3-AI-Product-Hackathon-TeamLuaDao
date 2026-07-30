"""PostgreSQL repository that persists hashes and metadata only."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Protocol, Sequence

import psycopg
from fastapi import Depends
from psycopg.rows import dict_row

from chan_ml.indicators import PREFIX_LENGTH

from .config import IntelConfig, get_config
from .models import (
    FetchResult,
    LookupRecord,
    ReportReceiptRecord,
    SourceState,
    SourceStatusRecord,
)
from .schemas import IndicatorReportSubmission


class IntelRepository(Protocol):
    def get_source_state(self, source: str) -> SourceState | None: ...

    def apply_snapshot(self, result: FetchResult) -> int: ...

    def record_sync_failure(self, source: str, error_code: str) -> None: ...

    def lookup(self, kind: str, prefix: str) -> list[LookupRecord]: ...

    def submit_reports(
        self, items: Sequence[IndicatorReportSubmission], actor: str
    ) -> list[ReportReceiptRecord]: ...

    def review_report(
        self,
        report_id: str,
        decision: str,
        reason: str,
        actor: str,
        consensus_threshold: int,
    ) -> tuple[str, int, bool] | None: ...

    def list_sources(self) -> list[SourceStatusRecord]: ...

    def expire_reports(self, retention_days: int = 14) -> int: ...


class PostgresIntelRepository:
    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("CHAN_DATABASE_URL is required")
        self.dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def get_source_state(self, source: str) -> SourceState | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT name, etag, last_modified, last_success_at,
                       last_record_count
                FROM intel_sources
                WHERE name = %s
                """,
                (source,),
            ).fetchone()
            if row is None:
                return None
            return SourceState(
                name=str(row["name"]),
                etag=row["etag"],
                last_modified=row["last_modified"],
                last_success_at=row["last_success_at"],
                last_record_count=int(row["last_record_count"]),
            )

    def apply_snapshot(self, result: FetchResult) -> int:
        run_id = uuid.uuid4()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                source = cursor.execute(
                    "SELECT enabled FROM intel_sources WHERE name = %s FOR UPDATE",
                    (result.source,),
                ).fetchone()
                if source is None:
                    raise RuntimeError("intel_source_not_registered")
                if not bool(source["enabled"]):
                    raise RuntimeError("intel_source_disabled")
                cursor.execute(
                    """
                    INSERT INTO intel_sync_runs (id, source, status)
                    VALUES (%s, %s, 'running')
                    """,
                    (run_id, result.source),
                )
                if not result.modified:
                    cursor.execute(
                        """
                        UPDATE intel_sync_runs
                        SET status = 'unchanged', finished_at = now(),
                            record_count = 0
                        WHERE id = %s
                        """,
                        (run_id,),
                    )
                    cursor.execute(
                        """
                        UPDATE intel_sources
                        SET etag = COALESCE(%s, etag),
                            last_modified = COALESCE(%s, last_modified),
                            last_success_at = now(),
                            last_error_code = NULL,
                            updated_at = now()
                        WHERE name = %s
                        """,
                        (result.etag, result.last_modified, result.source),
                    )
                    return 0

                cursor.executemany(
                    """
                    INSERT INTO threat_indicators (
                        kind, hash, prefix, origin, source_item_hash,
                        confidence, first_seen, last_seen, active,
                        last_sync_run_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, %s)
                    ON CONFLICT (kind, hash, origin) DO UPDATE
                    SET source_item_hash = EXCLUDED.source_item_hash,
                        confidence = EXCLUDED.confidence,
                        first_seen = LEAST(
                            threat_indicators.first_seen,
                            EXCLUDED.first_seen
                        ),
                        last_seen = GREATEST(
                            threat_indicators.last_seen,
                            EXCLUDED.last_seen
                        ),
                        active = true,
                        last_sync_run_id = EXCLUDED.last_sync_run_id,
                        updated_at = now()
                    """,
                    [
                        (
                            item.kind,
                            item.digest,
                            item.prefix,
                            result.source,
                            item.source_item_hash,
                            item.confidence,
                            item.first_seen,
                            item.last_seen,
                            run_id,
                        )
                        for item in result.indicators
                    ],
                )
                # Bulk feeds are full snapshots. Entries absent from the latest
                # successful snapshot become inactive rather than being erased.
                cursor.execute(
                    """
                    UPDATE threat_indicators
                    SET active = false, updated_at = now()
                    WHERE origin = %s
                      AND active
                      AND last_sync_run_id IS DISTINCT FROM %s
                    """,
                    (result.source, run_id),
                )
                count = len(result.indicators)
                cursor.execute(
                    """
                    UPDATE intel_sync_runs
                    SET status = 'succeeded', finished_at = now(),
                        record_count = %s
                    WHERE id = %s
                    """,
                    (count, run_id),
                )
                cursor.execute(
                    """
                    UPDATE intel_sources
                    SET etag = %s,
                        last_modified = %s,
                        last_success_at = now(),
                        last_record_count = %s,
                        last_error_code = NULL,
                        updated_at = now()
                    WHERE name = %s
                    """,
                    (
                        result.etag,
                        result.last_modified,
                        count,
                        result.source,
                    ),
                )
                return count

    def record_sync_failure(self, source: str, error_code: str) -> None:
        run_id = uuid.uuid4()
        safe_code = error_code[:128]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO intel_sync_runs (
                    id, source, status, finished_at, error_code
                ) VALUES (%s, %s, 'failed', now(), %s)
                """,
                (run_id, source, safe_code),
            )
            connection.execute(
                """
                UPDATE intel_sources
                SET last_error_code = %s, updated_at = now()
                WHERE name = %s
                """,
                (safe_code, source),
            )

    def lookup(self, kind: str, prefix: str) -> list[LookupRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT encode(hash, 'hex') AS digest_hex,
                       MAX(report_count) AS report_count,
                       MIN(first_seen) AS first_seen,
                       MAX(last_seen) AS last_seen,
                       CASE
                           WHEN bool_or(confidence = 'partner_verified')
                               THEN 'partner_verified'
                           WHEN bool_or(confidence = 'verified')
                               THEN 'verified'
                           WHEN bool_or(confidence = 'community_reviewed')
                               THEN 'community_reviewed'
                           ELSE 'feed_listed'
                       END AS confidence
                FROM threat_indicators
                WHERE kind = %s
                  -- Left-anchored LIKE narrows on the indexed char(5) column and
                  -- stays correct for any configured prefix length. The former
                  -- `prefix = substring(%%s FROM 1 FOR 2)` was left over from the
                  -- two-hex contract: after migration 002 widened the column to
                  -- char(5) it could never match, so every lookup returned empty.
                  AND prefix LIKE %s
                  AND substring(
                      encode(hash, 'hex') FROM 1 FOR %s
                  ) = %s
                  AND active
                GROUP BY hash
                ORDER BY hash
                LIMIT 500
                """,
                (kind, prefix + "%", len(prefix), prefix),
            ).fetchall()
            return [
                LookupRecord(
                    digest_hex=str(row["digest_hex"]),
                    report_count=int(row["report_count"]),
                    first_seen=row["first_seen"],
                    last_seen=row["last_seen"],
                    confidence=str(row["confidence"]),
                )
                for row in rows
            ]

    def submit_reports(
        self, items: Sequence[IndicatorReportSubmission], actor: str
    ) -> list[ReportReceiptRecord]:
        receipts: list[ReportReceiptRecord] = []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for item in items:
                    report_id = uuid.uuid4()
                    digest = bytes.fromhex(item.indicator_hash)
                    reporter_hash = bytes.fromhex(item.reporter_hash)
                    evidence_hash = (
                        bytes.fromhex(item.evidence_hash)
                        if item.evidence_hash
                        else None
                    )
                    cursor.execute(
                        """
                        INSERT INTO indicator_reports (
                            id, kind, hash, prefix, reporter_hash,
                            evidence_hash, consented, submitted_by
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, true, %s)
                        ON CONFLICT (kind, hash, reporter_hash) DO NOTHING
                        RETURNING id, status
                        """,
                        (
                            report_id,
                            item.kind,
                            digest,
                            # Must equal the first PREFIX_LENGTH hex characters of
                            # the hash: migration 002 enforces that with a CHECK.
                            # A hardcoded [:2] here made every community report
                            # fail with a constraint violation.
                            item.indicator_hash[:PREFIX_LENGTH],
                            reporter_hash,
                            evidence_hash,
                            actor,
                        ),
                    )
                    inserted = cursor.fetchone()
                    if inserted:
                        cursor.execute(
                            """
                            INSERT INTO indicator_report_audit (
                                report_id, action, actor
                            ) VALUES (%s, 'submitted', %s)
                            """,
                            (report_id, actor),
                        )
                        receipts.append(
                            ReportReceiptRecord(
                                id=str(inserted["id"]),
                                status=str(inserted["status"]),
                                duplicate=False,
                            )
                        )
                        continue
                    existing = cursor.execute(
                        """
                        SELECT id, status
                        FROM indicator_reports
                        WHERE kind = %s AND hash = %s AND reporter_hash = %s
                        """,
                        (item.kind, digest, reporter_hash),
                    ).fetchone()
                    if existing is None:
                        raise RuntimeError("indicator_report_deduplication_failed")
                    receipts.append(
                        ReportReceiptRecord(
                            id=str(existing["id"]),
                            status=str(existing["status"]),
                            duplicate=True,
                        )
                    )
        return receipts

    def review_report(
        self,
        report_id: str,
        decision: str,
        reason: str,
        actor: str,
        consensus_threshold: int,
    ) -> tuple[str, int, bool] | None:
        target_status = "approved" if decision == "approve" else "rejected"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = cursor.execute(
                    """
                    SELECT kind, hash, prefix, status, submitted_by, submitted_at
                    FROM indicator_reports
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (report_id,),
                ).fetchone()
                if (
                    row is None
                    or row["status"] != "quarantined"
                    or row["submitted_by"] == actor
                ):
                    return None
                # Serialize reviews for the same indicator. Without this lock,
                # two simultaneous second reports could each observe only one
                # committed approval and fail to activate consensus.
                cursor.execute(
                    """
                    SELECT pg_advisory_xact_lock(
                        hashtextextended(encode(%s, 'hex'), 0)
                    )
                    """,
                    (row["hash"],),
                )
                cursor.execute(
                    """
                    UPDATE indicator_reports
                    SET status = %s,
                        reviewed_by = %s,
                        reviewed_at = now(),
                        review_reason = %s
                    WHERE id = %s AND status = 'quarantined'
                    """,
                    (target_status, actor, reason, report_id),
                )
                cursor.execute(
                    """
                    INSERT INTO indicator_report_audit (
                        report_id, action, actor, reason_code
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (report_id, target_status, actor, reason),
                )
                if target_status == "rejected":
                    return target_status, 0, False

                consensus = cursor.execute(
                    """
                    SELECT COUNT(DISTINCT reporter_hash) AS count,
                           MIN(submitted_at) AS first_seen,
                           MAX(submitted_at) AS last_seen
                    FROM indicator_reports
                    WHERE kind = %s AND hash = %s AND status = 'approved'
                    """,
                    (row["kind"], row["hash"]),
                ).fetchone()
                if consensus is None:
                    raise RuntimeError("indicator_report_consensus_failed")
                count = int(consensus["count"])
                activated = count >= consensus_threshold
                if activated:
                    source_item_hash = bytes(row["hash"])
                    cursor.execute(
                        """
                        INSERT INTO threat_indicators (
                            kind, hash, prefix, origin, source_item_hash,
                            confidence, report_count, first_seen, last_seen,
                            active
                        )
                        VALUES (
                            %s, %s, %s, 'user_report', %s,
                            'community_reviewed', %s, %s, %s, true
                        )
                        ON CONFLICT (kind, hash, origin) DO UPDATE
                        SET report_count = EXCLUDED.report_count,
                            first_seen = LEAST(
                                threat_indicators.first_seen,
                                EXCLUDED.first_seen
                            ),
                            last_seen = GREATEST(
                                threat_indicators.last_seen,
                                EXCLUDED.last_seen
                            ),
                            confidence = 'community_reviewed',
                            active = true,
                            updated_at = now()
                        """,
                        (
                            row["kind"],
                            row["hash"],
                            row["prefix"],
                            source_item_hash,
                            count,
                            consensus["first_seen"],
                            consensus["last_seen"],
                        ),
                    )
                return target_status, count, activated

    def list_sources(self) -> list[SourceStatusRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT name, enabled, rights_basis, update_interval_minutes,
                       last_success_at, last_record_count, last_error_code
                FROM intel_sources
                ORDER BY name
                """
            ).fetchall()
            return [
                SourceStatusRecord(
                    name=str(row["name"]),
                    enabled=bool(row["enabled"]),
                    rights_basis=str(row["rights_basis"]),
                    update_interval_minutes=row["update_interval_minutes"],
                    last_success_at=row["last_success_at"],
                    last_record_count=int(row["last_record_count"]),
                    last_error_code=row["last_error_code"],
                )
                for row in rows
            ]

    def expire_reports(self, retention_days: int = 14) -> int:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                rows = cursor.execute(
                    """
                    UPDATE indicator_reports
                    SET status = 'expired'
                    WHERE status = 'quarantined'
                      AND submitted_at < now() - (%s * interval '1 day')
                    RETURNING id
                    """,
                    (retention_days,),
                ).fetchall()
                if rows:
                    cursor.executemany(
                        """
                        INSERT INTO indicator_report_audit (
                            report_id, action, actor, reason_code
                        ) VALUES (%s, 'expired', 'system', 'quarantine_ttl')
                        """,
                        [(row["id"],) for row in rows],
                    )
                return len(rows)


def get_repository(
    config: IntelConfig = Depends(get_config),
) -> PostgresIntelRepository:
    return PostgresIntelRepository(config.database_url)
