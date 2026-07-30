"""Data access for the public /v1 service.

Deliberately does NOT import chan_training_api: the public process must not be
able to reach the quarantine or training tables even by accident. It also uses
a connection pool, unlike the cron-scale control plane, because /v1/analyze has
a p95 budget of five seconds (§11.4).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Protocol, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from chan_ml.redact import PREFIX_LENGTH

_KIND_TABLES = {
    "account": "blocklist_accounts",
    "phone": "blocklist_phones",
    "url": "blocklist_urls",
}


def _table_for(kind: str) -> str:
    try:
        return _KIND_TABLES[kind]
    except KeyError as error:
        raise ValueError(f"unknown blocklist kind: {kind}") from error


@dataclass(frozen=True)
class Device:
    id: str
    platform: str
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class BlocklistEntry:
    hash: str
    report_cnt: int
    first_seen: datetime
    last_seen: datetime
    origin: str


@dataclass(frozen=True)
class ActiveModel:
    version: str
    artifact_uri: str
    artifact_sha256: str


@dataclass(frozen=True)
class SimilarScenario:
    similarity: float
    labels: tuple[str, ...]
    risk: str | None


class GatewayRepository(Protocol):
    """The surface the routers depend on, so tests can substitute a fake."""

    def create_device(
        self, *, platform: str, token_hash: bytes, ttl_days: int,
        push_token: str | None = None, rotated_from: str | None = None,
    ) -> Device: ...

    def device_for_token(self, token_hash: bytes) -> Device | None: ...

    def touch_device(self, device_id: str) -> None: ...

    def blocklist_cluster(self, kind: str, prefix: str) -> list[BlocklistEntry]: ...

    def blocklist_contains(self, kind: str, digests: Sequence[str]) -> bool: ...

    def report_identifier(self, kind: str, digest: str, origin: str) -> int: ...

    def count_reports_today(self, device_id: str) -> int: ...

    def record_analysis(self, **fields: Any) -> None: ...

    def analysis_exists(self, analysis_id: str) -> bool: ...

    def record_feedback(
        self, *, analysis_id: str, verdict: str, contributed: bool
    ) -> bool: ...

    def record_access(
        self, *, device_id: str | None, endpoint: str, status: int, latency_ms: int
    ) -> None: ...

    def get_active_model(self) -> ActiveModel | None: ...

    def similar_scenarios(
        self, embedding: Sequence[float], *, limit: int = 5
    ) -> list[SimilarScenario]: ...

    def hit_rate_limit(self, bucket: str, limit: int, window_seconds: int) -> bool: ...

    def purge_expired(
        self, *, analyses_days: int, access_log_days: int
    ) -> dict[str, int]: ...


class PostgresGatewayRepository:
    """psycopg3 implementation. Should run under a least-privilege DB role."""

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 8) -> None:
        if not dsn:
            raise RuntimeError("CHAN_DATABASE_URL is required")
        self._pool = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    def close(self) -> None:
        self._pool.close()

    # --- devices ----------------------------------------------------------

    def create_device(
        self,
        *,
        platform: str,
        token_hash: bytes,
        ttl_days: int,
        push_token: str | None = None,
        rotated_from: str | None = None,
    ) -> Device:
        device_id = f"dev_{secrets.token_hex(12)}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO devices
                  (id, token_hash, platform, push_token, rotated_from, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, platform, expires_at, revoked_at
                """,
                (device_id, token_hash, platform, push_token, rotated_from, expires_at),
            ).fetchone()
            if rotated_from:
                connection.execute(
                    "UPDATE devices SET revoked_at = now() WHERE id = %s",
                    (rotated_from,),
                )
        assert row is not None
        return Device(**row)

    def device_for_token(self, token_hash: bytes) -> Device | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                SELECT id, platform, expires_at, revoked_at
                FROM devices
                WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > now()
                """,
                (token_hash,),
            ).fetchone()
        return Device(**row) if row else None

    def touch_device(self, device_id: str) -> None:
        with self._pool.connection() as connection:
            connection.execute(
                "UPDATE devices SET last_seen_at = now() WHERE id = %s", (device_id,)
            )

    # --- blocklist / lookup ----------------------------------------------

    def blocklist_cluster(self, kind: str, prefix: str) -> list[BlocklistEntry]:
        table = _table_for(kind)
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT encode(hash, 'hex') AS hash, report_cnt,
                       first_seen, last_seen, origin
                FROM {table}
                WHERE prefix = %s
                ORDER BY hash
                """,
                (prefix,),
            ).fetchall()
        return [BlocklistEntry(**row) for row in rows]

    def blocklist_contains(self, kind: str, digests: Sequence[str]) -> bool:
        if not digests:
            return False
        table = _table_for(kind)
        with self._pool.connection() as connection:
            row = connection.execute(
                f"SELECT 1 FROM {table} WHERE hash = ANY(%s) LIMIT 1",
                ([bytes.fromhex(digest) for digest in digests],),
            ).fetchone()
        return row is not None

    def report_identifier(self, kind: str, digest: str, origin: str) -> int:
        table = _table_for(kind)
        with self._pool.connection() as connection:
            row = connection.execute(
                f"""
                INSERT INTO {table} (hash, prefix, origin)
                VALUES (%s, %s, %s)
                ON CONFLICT (hash) DO UPDATE
                  SET report_cnt = {table}.report_cnt + 1, last_seen = now()
                RETURNING report_cnt
                """,
                (bytes.fromhex(digest), digest[:PREFIX_LENGTH], origin),
            ).fetchone()
        assert row is not None
        return int(row["report_cnt"])

    def count_reports_today(self, device_id: str) -> int:
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                SELECT count(*) AS count FROM access_log
                WHERE device_id = %s AND endpoint = 'POST /v1/report'
                  AND status < 400 AND created_at > now() - interval '1 day'
                """,
                (device_id,),
            ).fetchone()
        return int(row["count"]) if row else 0

    # --- analyses / feedback ---------------------------------------------

    def record_analysis(self, **fields: Any) -> None:
        with self._pool.connection() as connection:
            connection.execute(
                """
                INSERT INTO analyses
                  (id, text_sha256, risk, score, signals, source, input_mode,
                   app_package, truncated, blocklist_match, engine_version,
                   rule_version, device_id)
                VALUES
                  (%(id)s, %(text_sha256)s, %(risk)s, %(score)s, %(signals)s,
                   %(source)s, %(input_mode)s, %(app_package)s, %(truncated)s,
                   %(blocklist_match)s, %(engine_version)s, %(rule_version)s,
                   %(device_id)s)
                ON CONFLICT (id) DO NOTHING
                """,
                {**fields, "signals": Jsonb(fields["signals"])},
            )

    def analysis_exists(self, analysis_id: str) -> bool:
        with self._pool.connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM analyses WHERE id = %s", (analysis_id,)
            ).fetchone()
        return row is not None

    def record_feedback(
        self, *, analysis_id: str, verdict: str, contributed: bool
    ) -> bool:
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO feedback (analysis_id, verdict, contributed)
                VALUES (%s, %s, %s)
                ON CONFLICT (analysis_id) DO UPDATE
                  SET verdict = EXCLUDED.verdict,
                      contributed = feedback.contributed OR EXCLUDED.contributed
                RETURNING id
                """,
                (analysis_id, verdict, contributed),
            ).fetchone()
        return row is not None

    def record_access(
        self, *, device_id: str | None, endpoint: str, status: int, latency_ms: int
    ) -> None:
        with self._pool.connection() as connection:
            connection.execute(
                """
                INSERT INTO access_log (device_id, endpoint, status, latency_ms)
                VALUES (%s, %s, %s, %s)
                """,
                (device_id, endpoint, status, latency_ms),
            )

    # --- model registry (read-only) --------------------------------------

    def get_active_model(self) -> ActiveModel | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                SELECT version, artifact_uri, artifact_sha256
                FROM model_versions WHERE status = 'active'
                """
            ).fetchone()
        return ActiveModel(**row) if row else None

    # --- similarity -------------------------------------------------------

    def similar_scenarios(
        self, embedding: Sequence[float], *, limit: int = 5
    ) -> list[SimilarScenario]:
        vector = "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"
        with self._pool.connection() as connection:
            rows = connection.execute(
                """
                SELECT 1 - (embedding <=> %s::vector) AS similarity, labels, risk
                FROM scenarios
                WHERE embedding IS NOT NULL AND consented
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vector, vector, limit),
            ).fetchall()
        return [
            SimilarScenario(
                similarity=float(row["similarity"]),
                labels=tuple(row["labels"] or ()),
                risk=row["risk"],
            )
            for row in rows
        ]

    # --- rate limiting fallback ------------------------------------------

    def hit_rate_limit(self, bucket: str, limit: int, window_seconds: int) -> bool:
        """Return True when the caller is over budget. Postgres fallback path."""
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO rate_limit_counters (bucket, hits, expires_at)
                VALUES (%s, 1, now() + make_interval(secs => %s))
                ON CONFLICT (bucket) DO UPDATE SET
                  hits = CASE
                           WHEN rate_limit_counters.expires_at < now() THEN 1
                           ELSE rate_limit_counters.hits + 1
                         END,
                  expires_at = CASE
                                 WHEN rate_limit_counters.expires_at < now()
                                 THEN now() + make_interval(secs => %s)
                                 ELSE rate_limit_counters.expires_at
                               END
                RETURNING hits
                """,
                (bucket, window_seconds, window_seconds),
            ).fetchone()
        return bool(row) and int(row["hits"]) > limit

    # --- retention (§7.2) -------------------------------------------------

    def purge_expired(
        self, *, analyses_days: int, access_log_days: int
    ) -> dict[str, int]:
        with self._pool.connection() as connection:
            analyses = connection.execute(
                "DELETE FROM analyses WHERE created_at < now() - make_interval(days => %s)",
                (analyses_days,),
            ).rowcount
            access = connection.execute(
                "DELETE FROM access_log WHERE created_at < now() - make_interval(days => %s)",
                (access_log_days,),
            ).rowcount
            codes = connection.execute(
                "DELETE FROM guardian_pair_codes WHERE expires_at < now()"
            ).rowcount
            counters = connection.execute(
                "DELETE FROM rate_limit_counters WHERE expires_at < now()"
            ).rowcount
        return {
            "analyses": analyses or 0,
            "access_log": access or 0,
            "pair_codes": codes or 0,
            "rate_limit_counters": counters or 0,
        }
