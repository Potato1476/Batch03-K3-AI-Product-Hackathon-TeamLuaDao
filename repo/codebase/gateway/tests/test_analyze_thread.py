"""POST /v1/analyze-thread — the public edge of L5."""

from __future__ import annotations

HIJACKED = [
    {"sender": "contact", "text": "Chào cậu, dạo này công việc thế nào rồi? 😊"},
    {"sender": "user", "text": "Tớ vẫn ổn, cậu sao rồi"},
    {"sender": "contact", "text": "Mình cũng bình thường thôi. Cuối tuần rảnh không? ☕"},
    {"sender": "user", "text": "Chắc rảnh, sao thế"},
    {"sender": "contact", "text": "Đi cà phê nhé, lâu lắm không gặp rồi. 🙂"},
    {"sender": "contact", "text": "e dang ket tien qua, ck giup a 15 trieu vao stk 0912345678 duoc k"},
    {"sender": "user", "text": "Ơ sao gấp thế, gọi video cho tớ cái"},
    {"sender": "contact", "text": "dang hop k goi dc, nhan tin thoi, chuyen gap giup a"},
]


def _post(client, auth, messages, **extra):  # noqa: ANN001, ANN202
    body = {"messages": messages, "source": "web", **extra}
    return client.post("/v1/analyze-thread", json=body, headers=auth)


def test_hijacked_account_thread_is_flagged(client, auth) -> None:
    response = _post(client, auth, HIJACKED, contact_name="Minh")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["risk"] == "high"
    codes = {signal["code"] for signal in body["thread_signals"]}
    assert {"doi_giong_van", "ne_goi_thoai"} <= codes
    assert body["questions"]
    # Every finding carries a human label, not just a code.
    assert all(signal["label"] for signal in body["thread_signals"])


def test_thread_endpoint_requires_a_device_token(client) -> None:
    response = client.post(
        "/v1/analyze-thread", json={"messages": HIJACKED, "source": "web"}
    )
    assert response.status_code == 401


def test_thread_needs_at_least_two_messages(client, auth) -> None:
    response = _post(client, auth, [{"sender": "contact", "text": "chuyen 5 trieu"}])
    assert response.status_code == 422


def test_unknown_field_is_rejected(client, auth) -> None:
    response = _post(client, auth, HIJACKED, contact_id="12345")
    assert response.status_code == 422


def test_thread_verdict_is_not_persisted(client, auth, repository) -> None:
    """I2: no message content, and a thread has no analyses row to write."""
    before = len(repository.analyses)
    assert _post(client, auth, HIJACKED, contact_name="Minh").status_code == 200
    assert len(repository.analyses) == before


def test_thread_reports_the_rule_bundle_version(client, auth) -> None:
    body = _post(client, auth, HIJACKED, contact_name="Minh").json()
    assert body["rule_bundle_version"].startswith("rb-")


def test_a_real_friend_asking_to_borrow_is_not_flagged_high(client, auth) -> None:
    friendly = HIJACKED[:5] + [
        {
            "sender": "contact",
            "text": "Mà này, tháng này mình kẹt quá, cho mình mượn 2 triệu được không? 🙏",
        },
        {"sender": "user", "text": "Được chứ, gọi video cho tớ cái"},
        {"sender": "contact", "text": "Ok để mình gọi luôn nhé! 😄"},
    ]
    body = _post(client, auth, friendly, contact_name="Minh").json()
    assert body["risk"] != "high"
