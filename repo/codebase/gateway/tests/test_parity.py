"""Equivalence tests — §9 and §11.3.

The architecture's central promise is that Web, Android and Zalo OA are the same
product with different intake. §2.1 states the consequence precisely: the same
message submitted from either platform must come back with the same risk, the
same signal set and the same explanation. §7 adds that `source` is for analytics
only and must never change processing.

The full three-client E2E parity test needs the real clients and belongs in
tests/parity once they exist. What can be verified here is the server half: the
API surface treats every source identically.
"""

from __future__ import annotations

import pytest

from conftest import LEGITIMATE_TEXT, SCAM_TEXT

MESSAGES = [
    SCAM_TEXT,
    LEGITIMATE_TEXT,
    "Ma xac thuc 4821 vua gui, doc cho anh de kich hoat.",
    "Chuc mung ban da trung thuong 500 trieu, lien he zalo de nhan giai.",
    "Con dong hoc phi 2 trieu truoc thu 6 nhe, co chu nhiem thong bao.",
    "Tai app tai day de nhan ho tro: bit.ly/hotro-abc",
]


def _analyze(client, auth, text, **overrides):  # noqa: ANN001, ANN202
    body = {
        "text": text,
        "source": "web",
        "input_mode": "manual",
        "truncated": False,
        "locale": "vi-VN",
    }
    body.update(overrides)
    response = client.post("/v1/analyze", json=body, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def _comparable(body: dict) -> tuple:
    """Everything a user sees, minus the per-request id."""
    return (
        body["risk"],
        body["score"],
        tuple(sorted((s["code"], s["confidence"]) for s in body["signals"])),
        body["explanation"],
        tuple(body["questions"]),
        tuple(body["actions"]),
    )


@pytest.mark.parametrize("text", MESSAGES)
def test_all_three_sources_agree(client, auth, text: str) -> None:
    """§7: `source` is analytics only. It must not alter a single output field."""
    results = [
        _comparable(_analyze(client, auth, text, source=source))
        for source in ("web", "android", "zalo_oa")
    ]
    assert results[0] == results[1] == results[2], f"source changed the result for {text!r}"


@pytest.mark.parametrize("text", MESSAGES)
def test_input_mode_does_not_change_the_verdict(client, auth, text: str) -> None:
    """A message typed by hand and one read from a notification score the same."""
    manual = _comparable(_analyze(client, auth, text, input_mode="manual"))
    notification = _comparable(
        _analyze(
            client,
            auth,
            text,
            source="android",
            input_mode="notification",
            app_package="com.zing.zalo",
        )
    )
    assert manual == notification


@pytest.mark.parametrize("text", MESSAGES)
def test_the_same_message_scores_identically_on_repeat(client, auth, text: str) -> None:
    """Determinism: the same input must not drift between calls."""
    first = _comparable(_analyze(client, auth, text))
    second = _comparable(_analyze(client, auth, text))
    assert first == second


def test_app_package_does_not_change_the_verdict(client, auth) -> None:
    baseline = _comparable(_analyze(client, auth, SCAM_TEXT, source="android"))
    for package in ("com.zing.zalo", "com.facebook.orca", "com.android.mms"):
        candidate = _comparable(
            _analyze(
                client,
                auth,
                SCAM_TEXT,
                source="android",
                input_mode="notification",
                app_package=package,
            )
        )
        assert candidate == baseline


def test_engine_and_bundle_versions_are_reported_for_parity_checks(client, auth) -> None:
    """§7: these two fields exist so two clients can prove they match."""
    body = _analyze(client, auth, SCAM_TEXT)
    assert body["engine_version"]
    assert body["rule_bundle_version"]

    android = _analyze(client, auth, SCAM_TEXT, source="android")
    assert android["engine_version"] == body["engine_version"]
    assert android["rule_bundle_version"] == body["rule_bundle_version"]
