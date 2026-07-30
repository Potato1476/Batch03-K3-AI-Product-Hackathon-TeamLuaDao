from __future__ import annotations

import bz2
from datetime import UTC, datetime

import httpx
import pytest

from chan_intel.connectors.common import FeedError
from chan_intel.connectors.openphish import OpenPhishConnector
from chan_intel.connectors.phishtank import PhishTankConnector
from chan_intel.models import SourceState
from chan_intel.normalization import hash_url


def _state() -> SourceState:
    return SourceState(
        name="phishtank",
        etag='"old"',
        last_modified="Wed, 29 Jul 2026 00:00:00 GMT",
        last_success_at=datetime.now(UTC),
        last_record_count=1,
    )


def test_phishtank_connector_hashes_verified_online_urls():
    csv_body = (
        "phish_id,url,phish_detail_url,submission_time,verified,"
        "verification_time,online,target\n"
        "42,https://EVIL.example/login#token,http://detail,"
        "2026-07-29T10:00:00+00:00,yes,"
        "2026-07-29T10:05:00+00:00,yes,Example\n"
    ).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["if-none-match"] == '"old"'
        assert request.headers["user-agent"] == "chan-tests/test@example.org"
        return httpx.Response(
            200,
            headers={
                "etag": '"new"',
                "last-modified": "Thu, 30 Jul 2026 00:00:00 GMT",
            },
            content=bz2.compress(csv_body),
        )

    connector = PhishTankConnector(
        user_agent="chan-tests/test@example.org",
        transport=httpx.MockTransport(handler),
    )
    result = connector.fetch(_state())
    expected, _ = hash_url("https://evil.example/login")

    assert result.modified is True
    assert result.etag == '"new"'
    assert len(result.indicators) == 1
    assert result.indicators[0].digest == expected
    assert result.indicators[0].confidence == "verified"
    assert result.indicators[0].source_item_hash != expected


def test_phishtank_connector_handles_not_modified():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(304)

    result = PhishTankConnector(
        user_agent="chan-tests/test@example.org",
        transport=httpx.MockTransport(handler),
    ).fetch(_state())
    assert result.modified is False
    assert result.indicators == ()
    assert result.etag == '"old"'


def test_openphish_refuses_to_fetch_without_written_permission():
    connector = OpenPhishConnector(
        user_agent="chan-tests/test@example.org",
        license_confirmed=False,
        transport=httpx.MockTransport(
            lambda _request: pytest.fail("network must not be called")
        ),
    )
    with pytest.raises(
        FeedError, match="openphish_written_permission_required"
    ):
        connector.fetch()
