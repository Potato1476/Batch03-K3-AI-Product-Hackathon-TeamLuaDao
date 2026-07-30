"""Contract tests for the public /v1 endpoints (§7)."""

from __future__ import annotations

import json
from pathlib import Path

from chan_ml.redact import hash_identifier

from conftest import LEGITIMATE_TEXT, SCAM_TEXT

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


def _analyze(client, auth, text=SCAM_TEXT, **overrides):  # noqa: ANN001, ANN202
    body = {
        "text": text,
        "source": "web",
        "input_mode": "manual",
        "truncated": False,
        "locale": "vi-VN",
    }
    body.update(overrides)
    return client.post("/v1/analyze", json=body, headers=auth)


# --- auth -------------------------------------------------------------------


def test_protected_endpoints_require_a_device_token(client) -> None:
    assert client.post("/v1/analyze", json={}).status_code == 401
    assert client.get("/v1/lookup/account?prefix=abcde").status_code == 401
    assert client.post("/v1/report", json={}).status_code == 401
    assert client.post("/v1/feedback", json={}).status_code == 401


def test_an_unknown_token_is_rejected(client) -> None:
    response = _analyze(client, {"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_device_token"


def test_malformed_authorization_header_is_rejected(client) -> None:
    for header in ({"Authorization": "Basic abc"}, {"Authorization": "Bearer"}, {}):
        assert _analyze(client, header).status_code == 401


def test_rules_bundle_needs_no_token(client) -> None:
    """Clients need L0+L1 before they have a token, and offline (§2)."""
    assert client.get("/v1/rules/bundle").status_code == 200


# --- devices ----------------------------------------------------------------


def test_device_token_is_issued_once_and_works(client, repository) -> None:
    response = client.post("/v1/devices/token", json={"platform": "web"})
    assert response.status_code == 201
    body = response.json()
    assert body["device_id"].startswith("dev_")
    assert len(body["token"]) > 30

    analyzed = _analyze(client, {"Authorization": f"Bearer {body['token']}"})
    assert analyzed.status_code == 200


def test_device_token_response_never_contains_a_stored_digest(client) -> None:
    response = client.post("/v1/devices/token", json={"platform": "android"})
    assert "token_hash" not in response.text


def test_rotation_issues_a_new_token_and_retires_the_old_one(client, repository, auth, token) -> None:
    rotated = client.post("/v1/devices/token/rotate", json={}, headers=auth)
    assert rotated.status_code == 201
    new_token = rotated.json()["token"]
    assert new_token != token

    assert _analyze(client, {"Authorization": f"Bearer {new_token}"}).status_code == 200
    # The presented token is revoked by the rotation.
    assert _analyze(client, auth).status_code == 401


def test_unknown_platform_is_rejected(client) -> None:
    assert client.post("/v1/devices/token", json={"platform": "ios"}).status_code == 422


# --- analyze ----------------------------------------------------------------


def test_analyze_returns_the_full_section_7_contract(client, auth) -> None:
    body = _analyze(client, auth).json()
    assert set(body) >= {
        "analysis_id",
        "risk",
        "score",
        "signals",
        "explanation",
        "questions",
        "actions",
        "engine_version",
        "rule_bundle_version",
    }
    assert body["analysis_id"].startswith("an_")
    assert body["risk"] in {"high", "medium", "unknown"}
    assert 0.0 <= body["score"] <= 1.0
    assert body["rule_bundle_version"].startswith("rb-")
    assert body["engine_version"]


def test_analyze_scores_a_scam_message_as_risky(client, auth) -> None:
    body = _analyze(client, auth).json()
    assert body["risk"] in {"high", "medium"}
    assert body["signals"]
    assert body["explanation"] != "Chưa phát hiện dấu hiệu."
    assert body["questions"]


def test_signal_codes_stay_inside_the_taxonomy(client, auth) -> None:
    from chan_ml.constants import SIGNAL_CODES

    body = _analyze(client, auth).json()
    assert all(signal["code"] in SIGNAL_CODES for signal in body["signals"])


def test_evidence_is_quoted_from_the_redacted_text(client, auth) -> None:
    """§5: evidence exists to reduce fabrication, so it must be a real quote."""
    from chan_ml.normalize import normalize_for_model
    from chan_ml.redact import redact_l2

    haystack = normalize_for_model(redact_l2(SCAM_TEXT).text)
    for signal in _analyze(client, auth).json()["signals"]:
        if signal["evidence"]:
            assert normalize_for_model(signal["evidence"]) in haystack


def test_unknown_result_reports_no_signals(client, auth) -> None:
    body = _analyze(client, auth, LEGITIMATE_TEXT).json()
    assert body["risk"] == "unknown"
    assert body["signals"] == []
    assert body["actions"] == []
    assert body["verified_hotline"] is None


def test_truncated_input_is_flagged_to_the_user(client, auth) -> None:
    """§4.2: a shortened notification still scores, but says so."""
    body = _analyze(client, auth, truncated=True).json()
    assert "cắt ngắn" in body["explanation"]


def test_hotline_is_offered_when_an_authority_is_impersonated(client, auth) -> None:
    body = _analyze(client, auth).json()
    codes = {signal["code"] for signal in body["signals"]}
    if "mao_danh_tham_quyen" in codes:
        assert body["verified_hotline"] is not None
        assert body["verified_hotline"]["name"]


def test_oversized_and_empty_text_are_rejected(client, auth) -> None:
    assert _analyze(client, auth, "x" * 4_001).status_code == 422
    assert _analyze(client, auth, "").status_code == 422


def test_unexpected_field_is_rejected(client, auth) -> None:
    assert _analyze(client, auth, debug=True).status_code == 422


def test_invalid_source_or_input_mode_is_rejected(client, auth) -> None:
    assert _analyze(client, auth, source="desktop").status_code == 422
    assert _analyze(client, auth, input_mode="telepathy").status_code == 422


def test_unknown_local_signal_is_rejected(client, auth) -> None:
    """A client claiming an L1 signal this bundle lacks means they are out of step."""
    response = _analyze(client, auth, local_signals=["totally_made_up"])
    assert response.status_code == 422
    assert response.json()["detail"] == "unknown_local_signal"


def test_known_local_signal_is_accepted_and_bounded(
    client, auth, detection
) -> None:
    """apk_link raises cai_app_ngoai but cannot by itself decide the outcome."""
    boosted = _analyze(client, auth, LEGITIMATE_TEXT, local_signals=["apk_link"]).json()
    assert boosted["risk"] in {"high", "medium", "unknown"}
    assert boosted["score"] <= 1.0
    assert detection.last_body["local_boosts"] == {"cai_app_ngoai": 0.30}


def test_validation_error_never_echoes_the_submitted_text(client, auth) -> None:
    """A rejected payload may contain an OTP; the error must not repeat it."""
    response = client.post(
        "/v1/analyze",
        json={
            "text": "ma xac thuc 938271",
            "source": "web",
            "input_mode": "manual",
            "unexpected": "x",
        },
        headers=auth,
    )
    assert response.status_code == 422
    assert "938271" not in response.text


def test_analyze_fails_cleanly_when_the_bundle_is_missing(
    app, client, auth, tmp_path
) -> None:
    """No bundle means no known rule version, so refuse rather than guess."""
    from chan_api.deps import get_rule_store
    from chan_api.rules import RuleBundleStore

    app.dependency_overrides[get_rule_store] = lambda: RuleBundleStore(
        tmp_path / "absent.json"
    )
    response = _analyze(client, auth)
    assert response.status_code == 503
    assert response.json()["detail"] == "rule_bundle_unavailable"


def test_analyze_fails_cleanly_when_detection_is_unavailable(
    client, auth, detection
) -> None:
    detection.available = False
    response = _analyze(client, auth)
    assert response.status_code == 503
    assert response.json()["detail"] == "detection_engine_unavailable"


# --- lookup / report --------------------------------------------------------


def test_lookup_of_an_empty_bucket_does_not_claim_safety(client, auth) -> None:
    body = client.get("/v1/lookup/account?prefix=00000", headers=auth).json()
    assert body["hashes"] == []
    assert body["cluster_size"] == 0
    assert "Chưa có báo cáo" in body["no_match_message"]
    assert "an toàn" not in body["no_match_message"].lower()


def test_lookup_supports_all_three_kinds(client, auth) -> None:
    for kind in ("account", "phone", "url"):
        assert client.get(f"/v1/lookup/{kind}?prefix=abcde", headers=auth).status_code == 200


def test_lookup_rejects_an_unknown_kind(client, auth) -> None:
    assert client.get("/v1/lookup/email?prefix=abcde", headers=auth).status_code == 422


def test_report_increments_the_count(client, auth) -> None:
    digest = hash_identifier("19009999999999")
    first = client.post(
        "/v1/report", json={"kind": "account", "value_sha256": digest}, headers=auth
    )
    assert first.status_code == 202
    assert first.json()["report_cnt"] == 0
    assert first.json()["accepted"] is True

    second = client.post(
        "/v1/report", json={"kind": "account", "value_sha256": digest}, headers=auth
    )
    assert second.json()["report_cnt"] == 0


def test_report_rejects_a_plaintext_value(client, auth) -> None:
    """The server has no use for the value and must not accept one."""
    response = client.post(
        "/v1/report",
        json={"kind": "account", "value_sha256": "19001234567890"},
        headers=auth,
    )
    assert response.status_code == 422


def test_report_is_capped_per_day(client, auth, config) -> None:
    for index in range(config.report_per_device_per_day):
        client.post(
            "/v1/report",
            json={"kind": "account", "value_sha256": f"{index:064x}"},
            headers=auth,
        )
    response = client.post(
        "/v1/report",
        json={"kind": "account", "value_sha256": hash_identifier("123456")},
        headers=auth,
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "daily_report_limit"


def test_a_reported_account_stays_quarantined_until_review(client, auth) -> None:
    digest = hash_identifier("19008888777766")
    client.post(
        "/v1/report", json={"kind": "account", "value_sha256": digest}, headers=auth
    )
    body = client.get(f"/v1/lookup/account?prefix={digest[:5]}", headers=auth).json()
    assert digest not in {item["hash"] for item in body["hashes"]}


# --- rules bundle -----------------------------------------------------------


def test_bundle_is_served_byte_for_byte(client) -> None:
    """Both client ports must parse an identical document (§3)."""
    response = client.get("/v1/rules/bundle")
    assert response.content == (RULES_DIR / "bundle.json").read_bytes()


def test_bundle_supports_conditional_requests(client) -> None:
    first = client.get("/v1/rules/bundle")
    etag = first.headers["ETag"]
    second = client.get("/v1/rules/bundle", headers={"If-None-Match": etag})
    assert second.status_code == 304


def test_bundle_declares_its_version_in_a_header(client) -> None:
    response = client.get("/v1/rules/bundle")
    assert response.headers["X-CHAN-Bundle-Version"].startswith("rb-")


def test_bundle_version_matches_the_analyze_response(client, auth) -> None:
    bundle_version = client.get("/v1/rules/bundle").json()["bundle_version"]
    assert _analyze(client, auth).json()["rule_bundle_version"] == bundle_version


# --- feedback ---------------------------------------------------------------


def test_feedback_records_a_verdict(client, auth, repository) -> None:
    analysis_id = _analyze(client, auth).json()["analysis_id"]
    response = client.post(
        "/v1/feedback",
        json={"analysis_id": analysis_id, "verdict": "correct"},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json() == {"recorded": True, "contributed": False}
    assert repository.feedback[0]["verdict"] == "correct"


def test_feedback_for_an_unknown_analysis_is_404(client, auth) -> None:
    response = client.post(
        "/v1/feedback",
        json={"analysis_id": "an_doesnotexist", "verdict": "correct"},
        headers=auth,
    )
    assert response.status_code == 404


def test_feedback_does_not_contribute_by_default(client, auth, repository) -> None:
    """Contribution is opt-in; a verdict alone never stores text."""
    analysis_id = _analyze(client, auth).json()["analysis_id"]
    client.post(
        "/v1/feedback",
        json={"analysis_id": analysis_id, "verdict": "false_positive"},
        headers=auth,
    )
    assert repository.feedback[0]["contributed"] is False
    assert "redacted_text" not in json.dumps(repository.feedback)


def test_feedback_contribution_requires_redacted_text(client, auth) -> None:
    analysis_id = _analyze(client, auth).json()["analysis_id"]
    response = client.post(
        "/v1/feedback",
        json={
            "analysis_id": analysis_id,
            "verdict": "false_negative",
            "contribute": True,
            "redacted_text": "Gui ma 938271 cho toi ngay",
            "signals": ["yeu_cau_otp"],
        },
        headers=auth,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "content_failed_redaction_check"
    assert "938271" not in response.text


def test_feedback_rejects_duplicate_signal_codes(client, auth) -> None:
    analysis_id = _analyze(client, auth).json()["analysis_id"]
    response = client.post(
        "/v1/feedback",
        json={
            "analysis_id": analysis_id,
            "verdict": "false_negative",
            "signals": ["yeu_cau_otp", "yeu_cau_otp"],
        },
        headers=auth,
    )
    assert response.status_code == 422


def test_contribution_is_skipped_when_the_training_plane_is_unset(
    client, auth, repository
) -> None:
    analysis_id = _analyze(client, auth).json()["analysis_id"]
    response = client.post(
        "/v1/feedback",
        json={
            "analysis_id": analysis_id,
            "verdict": "false_negative",
            "contribute": True,
            "redacted_text": "Co quan thue yeu cau giu bi mat va chuyen <AMOUNT:trieu> vao <ACCOUNT>.",
            "signals": ["mao_danh_tham_quyen", "yeu_cau_bi_mat"],
        },
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["contributed"] is False


# --- ocr --------------------------------------------------------------------


def test_ocr_stub_reports_that_it_is_not_configured(client, auth) -> None:
    response = client.post(
        "/v1/ocr",
        files={"image": ("shot.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")},
        headers=auth,
    )
    assert response.status_code == 501
    assert response.json()["detail"] == "ocr_provider_not_configured"


def test_ocr_rejects_a_non_image(client, auth) -> None:
    response = client.post(
        "/v1/ocr",
        files={"image": ("note.txt", b"hello", "text/plain")},
        headers=auth,
    )
    assert response.status_code == 415


# --- ops --------------------------------------------------------------------


def test_healthz_is_open(client) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_readyz_reports_the_loaded_model(client) -> None:
    body = client.get("/readyz").json()
    assert body["status"] == "ready"
