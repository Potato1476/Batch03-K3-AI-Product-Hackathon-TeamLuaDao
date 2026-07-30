"""Import a reviewed CC BY 4.0 PhishVN CSV snapshot without storing raw URLs."""

from __future__ import annotations

import argparse
import csv
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from .connectors.common import FeedError, safe_datetime, source_item_digest
from .models import FetchResult, HashedIndicator
from .normalization import hash_url
from .repository import PostgresIntelRepository

POSITIVE_LABELS = {
    "1",
    "true",
    "yes",
    "phish",
    "phishing",
    "malicious",
}


def parse_phishvn_csv(
    path: Path,
    *,
    url_column: str,
    label_column: str,
    id_column: str | None,
    first_seen_column: str | None,
) -> FetchResult:
    now = datetime.now(UTC)
    indicators: dict[bytes, HashedIndicator] = {}
    total_rows = 0
    positive_rows = 0
    invalid_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        required = {url_column, label_column}
        if not required.issubset(fields):
            raise FeedError("phishvn_missing_required_columns")
        if id_column and id_column not in fields:
            raise FeedError("phishvn_missing_id_column")
        if first_seen_column and first_seen_column not in fields:
            raise FeedError("phishvn_missing_first_seen_column")

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1
            label = row.get(label_column, "").strip().lower()
            if label not in POSITIVE_LABELS:
                continue
            positive_rows += 1
            try:
                digest, prefix = hash_url(row[url_column])
            except (KeyError, ValueError):
                invalid_rows += 1
                continue
            external_id = (
                row.get(id_column, "").strip()
                if id_column
                else f"row-{row_number}"
            )
            if not external_id:
                external_id = f"row-{row_number}"
            first_seen = safe_datetime(
                row.get(first_seen_column) if first_seen_column else None,
                now,
            )
            indicators[digest] = HashedIndicator(
                kind="url",
                digest=digest,
                prefix=prefix,
                source_item_hash=source_item_digest("phishvn", external_id),
                first_seen=first_seen,
                last_seen=now,
                confidence="feed_listed",
            )

    if total_rows == 0:
        raise FeedError("phishvn_empty_snapshot")
    if positive_rows == 0:
        raise FeedError("phishvn_no_positive_rows")
    if invalid_rows / positive_rows > 0.05:
        raise FeedError("phishvn_excessive_invalid_rows")
    return FetchResult(
        source="phishvn",
        modified=True,
        indicators=tuple(indicators.values()),
        etag=None,
        last_modified=None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a local PhishVN CC BY 4.0 CSV snapshot"
    )
    parser.add_argument("source", choices=("phishvn",))
    parser.add_argument("path", type=Path)
    parser.add_argument("--url-column", default="url")
    parser.add_argument("--label-column", default="label")
    parser.add_argument("--id-column")
    parser.add_argument("--first-seen-column")
    parser.add_argument(
        "--confirm-cc-by-4",
        action="store_true",
        help="Required acknowledgement of the dataset attribution obligation",
    )
    args = parser.parse_args()
    if not args.confirm_cc_by_4:
        raise SystemExit("import_refused:cc_by_4_attribution_not_confirmed")
    if not args.path.is_file():
        raise SystemExit("import_refused:snapshot_file_not_found")

    try:
        result = parse_phishvn_csv(
            args.path,
            url_column=args.url_column,
            label_column=args.label_column,
            id_column=args.id_column,
            first_seen_column=args.first_seen_column,
        )
        repository = PostgresIntelRepository(
            os.environ.get("CHAN_DATABASE_URL", "")
        )
        count = repository.apply_snapshot(result)
    except psycopg.Error:
        raise SystemExit("import_failed:database_error") from None
    except (FeedError, RuntimeError, OSError) as error:
        raise SystemExit(f"import_failed:{error}") from None
    print(f"source=phishvn imported={count}")


if __name__ == "__main__":
    main()
