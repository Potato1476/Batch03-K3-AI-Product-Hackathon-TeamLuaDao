"""Seed a demo blocklist so the lookup flow has something to find.

The blocklist is empty until a community exists, which makes the lookup screen
undemonstrable: every number comes back "chưa có báo cáo". This fills it with a
small, fixed, documented set.

Two rules this module will not break:

1. **The numbers cannot belong to anyone.** They are built from reserved-looking
   blocks (`0000…`, `0999 999 …`) that no Vietnamese carrier issues, so a lookup
   can never accuse a real subscriber of fraud.
2. **The data never claims to be a community report.** It is written under its
   own source name with `confidence = 'feed_listed'`, which the client renders as
   "có trong danh sách nguồn dữ liệu" — not "đã có người báo cáo". Seeding
   `user_report` would put words in the mouths of people who never spoke.

Chạy:
    .venv/bin/chan-intel-seed-demo --database-url "$CHAN_DATABASE_URL"
    .venv/bin/chan-intel-seed-demo --database-url "..." --remove   # gỡ sạch
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

from .normalization import hash_account, hash_phone, hash_url

#: Source name for every row this module writes. Anything under this name is
#: demo material and can be deleted with --remove without touching real feeds.
SOURCE_NAME = "demo_seed"

#: Reserved-looking blocks. Vietnamese mobile numbers are 10 digits opening with
#: 03/05/07/08/09 and a carrier prefix; none of these are issued to subscribers.
DEMO_PHONES: tuple[str, ...] = (
    "0000000001",
    "0000000002",
    "0000000003",
    "0999999901",
    "0999999902",
    "0999999903",
)

#: Account numbers long enough to pass client validation, obviously synthetic.
DEMO_ACCOUNTS: tuple[str, ...] = (
    "0000000000001",
    "0000000000002",
    "9999999999901",
    "9999999999902",
)

#: Domains inside RFC 2606 / RFC 6761 reserved names — cannot be registered.
DEMO_URLS: tuple[str, ...] = (
    "https://vcb-secure.example",
    "https://phatnguoi-gov.example",
    "https://trungthuong2026.example",
    "https://dichvucong-vn.invalid",
)

#: Report counts are fixed per entry so the screen shows a stable number across
#: runs. They describe demo rows, not people.
_REPORT_COUNTS = (3, 5, 8, 12, 17, 21)


def _rows() -> list[tuple[str, bytes, str, int]]:
    """(kind, digest, prefix, report_count) for every demo indicator."""
    rows: list[tuple[str, bytes, str, int]] = []
    for index, value in enumerate(DEMO_PHONES):
        digest, digest_hex = hash_phone(value)
        rows.append(("phone", digest, digest_hex[:5], _REPORT_COUNTS[index % len(_REPORT_COUNTS)]))
    for index, value in enumerate(DEMO_ACCOUNTS):
        digest, digest_hex = hash_account(value)
        rows.append(("account", digest, digest_hex[:5], _REPORT_COUNTS[index % len(_REPORT_COUNTS)]))
    for index, value in enumerate(DEMO_URLS):
        digest, digest_hex = hash_url(value)
        rows.append(("url", digest, digest_hex[:5], _REPORT_COUNTS[index % len(_REPORT_COUNTS)]))
    return rows


def seed(dsn: str) -> int:
    now = datetime.now(UTC)
    first_seen = now - timedelta(days=21)
    rows = _rows()
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO intel_sources (name, enabled, rights_basis)
                VALUES (%s, true, 'explicit_consent')
                ON CONFLICT (name) DO UPDATE SET enabled = true
                """,
                (SOURCE_NAME,),
            )
            for kind, digest, prefix, report_count in rows:
                cursor.execute(
                    """
                    INSERT INTO threat_indicators (
                        kind, hash, prefix, origin, source_item_hash,
                        confidence, report_count, first_seen, last_seen, active
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        'feed_listed', %s, %s, %s, true
                    )
                    ON CONFLICT (kind, hash, origin) DO UPDATE
                    SET report_count = EXCLUDED.report_count,
                        last_seen = EXCLUDED.last_seen,
                        active = true,
                        updated_at = now()
                    """,
                    (kind, digest, prefix, SOURCE_NAME, digest,
                     report_count, first_seen, now - timedelta(days=2)),
                )
        connection.commit()
    return len(rows)


def remove(dsn: str) -> int:
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM threat_indicators WHERE origin = %s", (SOURCE_NAME,)
            )
            deleted = cursor.rowcount
            cursor.execute("DELETE FROM intel_sources WHERE name = %s", (SOURCE_NAME,))
        connection.commit()
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--remove", action="store_true", help="Xoá sạch dữ liệu demo đã seed."
    )
    args = parser.parse_args()

    if args.remove:
        print(f"đã xoá {remove(args.database_url)} chỉ dấu demo")
        return
    count = seed(args.database_url)
    print(f"đã seed {count} chỉ dấu demo dưới nguồn '{SOURCE_NAME}'")
    print("  điện thoại:", ", ".join(DEMO_PHONES))
    print("  tài khoản :", ", ".join(DEMO_ACCOUNTS))
    print("  đường link:", ", ".join(DEMO_URLS))


if __name__ == "__main__":
    main()
