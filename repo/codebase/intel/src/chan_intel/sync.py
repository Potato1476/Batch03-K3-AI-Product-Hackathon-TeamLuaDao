"""Scheduled licensed-feed synchronization command."""

from __future__ import annotations

import argparse

import psycopg

from .config import IntelConfig, get_config
from .connectors import OpenPhishConnector, PhishTankConnector
from .connectors.common import FeedError
from .repository import PostgresIntelRepository


def connector_for(source: str, config: IntelConfig):
    user_agent = config.require_feed_user_agent()
    if source == "phishtank":
        return PhishTankConnector(
            user_agent=user_agent,
            app_key=config.phishtank_app_key,
            maximum_bytes=config.maximum_feed_bytes,
        )
    if source == "openphish":
        return OpenPhishConnector(
            user_agent=user_agent,
            license_confirmed=config.openphish_license_confirmed,
            maximum_bytes=config.maximum_feed_bytes,
        )
    raise ValueError("unsupported_intel_source")


def sync_source(
    source: str,
    repository: PostgresIntelRepository,
    config: IntelConfig,
) -> int:
    connector = connector_for(source, config)
    state = repository.get_source_state(source)
    if state is None:
        raise RuntimeError("intel_source_not_registered")
    try:
        result = connector.fetch(state)
        return repository.apply_snapshot(result)
    except FeedError as error:
        repository.record_sync_failure(source, error.code)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize a licensed threat-intelligence feed"
    )
    parser.add_argument(
        "source",
        choices=("phishtank", "openphish"),
        help="Fixed-host source adapter to run",
    )
    parser.add_argument(
        "--expire-reports",
        action="store_true",
        help="Also expire unreviewed reports older than 14 days",
    )
    args = parser.parse_args()

    config = get_config()
    repository = PostgresIntelRepository(config.database_url)
    try:
        count = sync_source(args.source, repository, config)
    except psycopg.Error:
        raise SystemExit("sync_failed:database_error") from None
    except (FeedError, RuntimeError, ValueError) as error:
        # Errors are operational codes only; raw indicators and key-bearing
        # feed URLs are never printed.
        raise SystemExit(f"sync_failed:{error}") from None
    expired = repository.expire_reports() if args.expire_reports else 0
    print(f"source={args.source} synchronized={count} expired_reports={expired}")


if __name__ == "__main__":
    main()
