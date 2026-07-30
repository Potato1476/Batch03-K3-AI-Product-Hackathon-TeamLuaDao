"""chan-blocklist-import — load reported identifiers into the blocklist.

§3 draws the external sources (tinnhiemmang.vn, checkscam.vn, NCSC/bank alerts)
as a one-way, read-only feed. This CLI is that boundary. It deliberately does not
scrape: what may be collected from those sites is an agreement question, not a
technical one (§13 places organisational data access in phase 4). Point it at a
file you are permitted to use.

Input is one identifier per line, or a CSV with a column of identifiers. Values
are normalised, hashed, and only the digest plus its 5-hex prefix is stored — the
plaintext never reaches the database.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterator

from chan_ml.redact import (
    hash_identifier,
    normalize_account,
    normalize_phone,
    normalize_url,
)

from .config import get_config
from .repository import PostgresGatewayRepository

_NORMALIZERS = {
    "account": normalize_account,
    "phone": normalize_phone,
    "url": normalize_url,
}


def _read_values(path: Path, column: str | None) -> Iterator[str]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if column is None:
                raise SystemExit("--column is required for CSV input")
            if reader.fieldnames and column not in reader.fieldnames:
                raise SystemExit(f"column not found: {column}")
            for row in reader:
                value = (row.get(column) or "").strip()
                if value:
                    yield value
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if value and not value.startswith("#"):
                yield value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chan-blocklist-import",
        description="Import hashed scam identifiers into the CHẮN blocklist.",
    )
    parser.add_argument("--kind", required=True, choices=sorted(_NORMALIZERS))
    parser.add_argument(
        "--source",
        required=True,
        choices=["tinnhiemmang", "checkscam", "ncsc", "bank", "user_report"],
    )
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--column", default=None, help="column name for CSV input")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="hash and count without writing to the database",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.file.exists():
        raise SystemExit(f"file not found: {args.file}")

    normalize = _NORMALIZERS[args.kind]
    digests: set[str] = set()
    skipped = 0
    for value in _read_values(args.file, args.column):
        normalized = normalize(value)
        if not normalized:
            skipped += 1
            continue
        digests.add(hash_identifier(normalized))

    if args.dry_run:
        print(f"kind={args.kind} unique={len(digests)} skipped={skipped} (dry run)")
        return

    repository = PostgresGatewayRepository(get_config().database_url)
    try:
        for digest in sorted(digests):
            repository.report_identifier(args.kind, digest, args.source)
    finally:
        repository.close()

    # Counts only. Printing an identifier here would defeat the point.
    print(f"kind={args.kind} imported={len(digests)} skipped={skipped}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
