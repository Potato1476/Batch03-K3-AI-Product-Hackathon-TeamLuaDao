"""Contract tests for the public detection API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from chan_detection.main import create_app, get_runtime


class FakeRuntime:
    model_version = "test-model"
    last_text: str | None = None

    def predict(self, redacted_text: str) -> dict[str, object]:
        self.last_text = redacted_text
        return {
            "risk": "high",
            "score": 0.91,
            "scam_confidence": 0.95,
            "signals": [
                {
                    "code": "yeu_cau_otp",
                    "confidence": 0.99,
                    "evidence": "gửi <OTP>",
                }
            ],
            "explanation": "Người gửi yêu cầu cung cấp mã xác nhận.",
            "questions": ["Tại sao họ cần mã xác nhận?"],
            "engine_version": "test-engine",
        }


def _client() -> tuple[TestClient, FakeRuntime]:
    app = create_app()
    runtime = FakeRuntime()
    app.dependency_overrides[get_runtime] = lambda: runtime
    return TestClient(app), runtime


def test_analyze_contract_does_not_echo_complete_input() -> None:
    client, runtime = _client()
    content = "Nhân viên giả yêu cầu gửi OTP 938271 ngay để mở khóa tài khoản."
    response = client.post(
        "/v1/analyze",
        json={
            "text": content,
            "source": "android",
            "input_mode": "notification",
            "truncated": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["risk"] == "high"
    assert payload["model_version"] == "test-model"
    assert payload["actions"][0] == "report"
    assert payload["analysis_id"].startswith("an_")
    assert content not in response.text
    assert runtime.last_text == (
        "Nhân viên giả yêu cầu gửi OTP <OTP> ngay để mở khóa tài khoản."
    )
    assert response.headers["cache-control"] == "no-store"


def test_raw_identifier_is_redacted_without_echo() -> None:
    client, runtime = _client()
    raw = "Nhân viên yêu cầu chuyển vào 1234 5678 9012 ngay."
    response = client.post(
        "/v1/analyze",
        json={
            "text": raw,
            "source": "web",
            "input_mode": "manual",
        },
    )
    assert response.status_code == 200
    assert raw not in response.text
    assert runtime.last_text == "Nhân viên yêu cầu chuyển vào <ACCOUNT> ngay."


def test_unknown_is_not_presented_as_safe() -> None:
    class UnknownRuntime:
        model_version = "test-model"

        @staticmethod
        def predict(_text: str) -> dict[str, object]:
            return {
                "risk": "unknown",
                "score": 0.03,
                "scam_confidence": 0.02,
                "signals": [],
                "explanation": "Chưa phát hiện dấu hiệu.",
                "questions": [],
                "engine_version": "test-engine",
            }

    app = create_app()
    app.dependency_overrides[get_runtime] = lambda: UnknownRuntime()
    client = TestClient(app)
    response = client.post(
        "/v1/analyze",
        json={
            "text": "Hẹn gặp bạn tại cửa hàng chính thức ngày mai.",
            "source": "web",
            "input_mode": "manual",
        },
    )
    assert response.status_code == 200
    assert response.json()["actions"] == ["verify_if_uncertain"]
