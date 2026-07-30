"""Apply idempotent CHẮN PostgreSQL migrations before serving traffic."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

MIGRATIONS = (
    Path("/app/training_api/migrations/001_continuous_training.sql"),
    Path("/app/gateway/migrations/002_public_v1.sql"),
    Path("/app/intel/migrations/001_threat_intel.sql"),
    Path("/app/intel/migrations/002_prefix_v2.sql"),
)


def main() -> None:
    database_url = os.environ["CHAN_DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        # Scaling may start several containers concurrently. Serializing schema
        # setup avoids two cold starts racing on the same DDL.
        connection.execute("SELECT pg_advisory_lock(2026073001)")
        try:
            for migration in MIGRATIONS:
                connection.execute(migration.read_text(encoding="utf-8"))
        finally:
            connection.execute("SELECT pg_advisory_unlock(2026073001)")


if __name__ == "__main__":
    main()
