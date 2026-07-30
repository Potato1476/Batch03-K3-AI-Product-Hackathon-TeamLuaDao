"""chan-retention — enforce the data lifecycle from §7.2.

    hash + signals + score : 90 days
    access log             : 30 days

A retention promise that nothing executes is not a promise. Run this daily
(cron / Cloud Run Job) alongside the training worker.
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import get_config
from .logging_safe import configure_logging, log_event
from .repository import PostgresGatewayRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chan-retention",
        description="Delete data past its retention window (§7.2).",
    )
    parser.add_argument("--analyses-days", type=int, default=None)
    parser.add_argument("--access-log-days", type=int, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_logging()
    config = get_config()
    repository = PostgresGatewayRepository(config.database_url)
    try:
        deleted = repository.purge_expired(
            analyses_days=args.analyses_days or config.analyses_retention_days,
            access_log_days=args.access_log_days or config.access_log_retention_days,
        )
    finally:
        repository.close()
    log_event("retention_run", deleted=sum(deleted.values()))
    print(json.dumps(deleted, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
