"""Round-trip tests against a real PostgreSQL.

Why these exist: `test_intel_api.py` substitutes a FakeRepository, so the SQL in
`PostgresIntelRepository` had no coverage at all. Two bugs lived there
undetected until the service was exercised end to end:

1. `submit_reports` wrote `indicator_hash[:2]` into `prefix`, while migration 002
   widened the column to char(5) and added
   `CHECK (prefix = substring(encode(hash,'hex') FROM 1 FOR 5))`. Every community
   report failed with a constraint violation — a 500 on POST /v1/report.
2. `lookup` filtered with `prefix = substring(%s FROM 1 FOR 2)`, which can never
   match a char(5) column. Lookups returned an empty cluster forever — a silent
   failure, worse than the crash, because it looks exactly like "no reports".

Both are invisible to a fake. Run with:

    CHAN_TEST_DATABASE_URL=postgresql://chan:chan@localhost:5432/chan \
      pytest -m postgres codebase/intel/tests
"""

from __future__ import annotations

import hashlib
import os
import uuid

import pytest

from chan_ml.indicators import PREFIX_LENGTH
from chan_intel.repository import PostgresIntelRepository
from chan_intel.schemas import IndicatorReportSubmission

pytestmark = pytest.mark.postgres

DSN = os.environ.get("CHAN_TEST_DATABASE_URL", "")

requires_postgres = pytest.mark.skipif(
    not DSN, reason="set CHAN_TEST_DATABASE_URL to run PostgreSQL round-trip tests"
)


@pytest.fixture
def repository() -> PostgresIntelRepository:
    return PostgresIntelRepository(DSN)


def _unique_digest() -> str:
    """A fresh indicator hash per test, so runs do not collide."""
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()


def _reporter(name: str) -> str:
    return hashlib.sha256(f"chan:reporter:v1:{name}".encode()).hexdigest()


def _submission(digest: str, reporter: str) -> IndicatorReportSubmission:
    return IndicatorReportSubmission(
        kind="account",
        indicator_hash=digest,
        reporter_hash=reporter,
        consented=True,
    )


@requires_postgres
def test_submitted_report_stores_the_full_prefix(repository) -> None:
    """Regression: a truncated prefix violates the migration-002 CHECK."""
    digest = _unique_digest()
    receipts = repository.submit_reports(
        [_submission(digest, _reporter("device-a"))], "gateway"
    )
    assert len(receipts) == 1
    assert receipts[0].status == "quarantined"
    assert receipts[0].duplicate is False


@requires_postgres
def test_same_reporter_twice_is_deduplicated(repository) -> None:
    digest = _unique_digest()
    reporter = _reporter("device-a")
    repository.submit_reports([_submission(digest, reporter)], "gateway")
    again = repository.submit_reports([_submission(digest, reporter)], "gateway")
    assert again[0].duplicate is True


@requires_postgres
def test_report_becomes_findable_only_after_independent_consensus(
    repository,
) -> None:
    """The whole Flow C path, through real SQL: report → review ×2 → lookup."""
    digest = _unique_digest()
    prefix = digest[:PREFIX_LENGTH]

    # Nothing is visible before any report.
    assert [item for item in repository.lookup("account", prefix)
            if item.digest_hex == digest] == []

    first = repository.submit_reports(
        [_submission(digest, _reporter("device-a"))], "gateway"
    )[0]
    second = repository.submit_reports(
        [_submission(digest, _reporter("device-b"))], "gateway"
    )[0]

    # Quarantined reports must not reach the blocklist.
    assert [item for item in repository.lookup("account", prefix)
            if item.digest_hex == digest] == []

    outcome = repository.review_report(
        first.id, "approve", "verified_by_analyst", "analyst", 2
    )
    assert outcome is not None
    _, independent, activated = outcome
    assert independent == 1
    assert activated is False, "one approval must not activate an indicator"

    assert [item for item in repository.lookup("account", prefix)
            if item.digest_hex == digest] == []

    outcome = repository.review_report(
        second.id, "approve", "verified_by_analyst", "analyst", 2
    )
    assert outcome is not None
    _, independent, activated = outcome
    assert independent == 2
    assert activated is True

    # Regression: the lookup query must actually find it now.
    found = [
        item for item in repository.lookup("account", prefix)
        if item.digest_hex == digest
    ]
    assert len(found) == 1, "activated indicator must be visible to lookup"
    assert found[0].report_count == 2
    assert found[0].confidence == "community_reviewed"


@requires_postgres
def test_lookup_returns_the_whole_prefix_cluster(repository) -> None:
    """I4: a lookup reveals a bucket, never a single answer.

    Two indicators sharing a prefix must both come back, otherwise the response
    would identify exactly which value the user asked about.
    """
    first = _unique_digest()
    prefix = first[:PREFIX_LENGTH]
    # A second digest forced into the same bucket.
    second = prefix + _unique_digest()[PREFIX_LENGTH:]

    for digest in (first, second):
        for device in ("device-a", "device-b"):
            receipt = repository.submit_reports(
                [_submission(digest, _reporter(f"{device}-{digest[:8]}"))], "gateway"
            )[0]
            repository.review_report(
                receipt.id, "approve", "verified_by_analyst", "analyst", 2
            )

    returned = {item.digest_hex for item in repository.lookup("account", prefix)}
    assert {first, second} <= returned


@requires_postgres
def test_submitter_cannot_review_own_report(repository) -> None:
    """Four eyes, enforced in SQL rather than in the router."""
    digest = _unique_digest()
    receipt = repository.submit_reports(
        [_submission(digest, _reporter("device-a"))], "gateway"
    )[0]
    assert (
        repository.review_report(
            receipt.id, "approve", "self_review", "gateway", 2
        )
        is None
    )


@requires_postgres
def test_rejected_report_never_activates(repository) -> None:
    digest = _unique_digest()
    prefix = digest[:PREFIX_LENGTH]
    receipts = [
        repository.submit_reports([_submission(digest, _reporter(device))], "gateway")[0]
        for device in ("device-a", "device-b")
    ]
    for receipt in receipts:
        repository.review_report(receipt.id, "reject", "not_a_scam", "analyst", 2)
    assert [item for item in repository.lookup("account", prefix)
            if item.digest_hex == digest] == []
