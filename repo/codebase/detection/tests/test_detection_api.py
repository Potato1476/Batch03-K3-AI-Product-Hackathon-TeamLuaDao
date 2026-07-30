"""Contract tests for the public detection API."""

from __future__ import annotations

from fastapi.testclient import TestClient
import httpx

from chan_detection.config import DetectionConfig
from chan_detection.main import create_app, get_intel_client, get_runtime
from chan_detection.runtime import ModelRuntime, RuntimeProvider
from chan_detection.security import require_gateway


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
    app.dependency_overrides[require_gateway] = lambda: None
    app.dependency_overrides[get_intel_client] = lambda: type(
        "FakeIntel", (), {"contains": staticmethod(lambda _redaction: False)}
    )()
    return TestClient(app), runtime


def test_analyze_contract_does_not_echo_complete_input() -> None:
    client, runtime = _client()
    content = "Nhân viên giả yêu cầu gửi OTP 938271 ngay để mở khóa tài khoản."
    response = client.post(
        "/internal/v1/analyze",
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
    assert runtime.last_text is None
    assert response.headers["cache-control"] == "no-store"


def test_raw_identifier_is_redacted_without_echo() -> None:
    client, runtime = _client()
    raw = "Nhân viên yêu cầu chuyển vào 1234 5678 9012 ngay."
    response = client.post(
        "/internal/v1/analyze",
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
    app.dependency_overrides[require_gateway] = lambda: None
    app.dependency_overrides[get_intel_client] = lambda: type(
        "FakeIntel", (), {"contains": staticmethod(lambda _redaction: False)}
    )()
    client = TestClient(app)
    response = client.post(
        "/internal/v1/analyze",
        json={
            "text": "Hẹn gặp bạn tại cửa hàng chính thức ngày mai.",
            "source": "web",
            "input_mode": "manual",
        },
    )
    assert response.status_code == 200
    assert response.json()["actions"] == ["verify_if_uncertain"]


def test_runtime_provider_loads_registry_metadata_and_keeps_last_good_model(
    monkeypatch,
) -> None:
    config = DetectionConfig(
        training_api_url="http://training.test",
        training_api_key="training-key",
        intel_api_url="http://intel.test",
        detection_api_key="detection-key",
        model_poll_seconds=5,
    )
    provider = RuntimeProvider(config)
    runtime = FakeRuntime()
    metadata = {
        "version": runtime.model_version,
        "artifact_uri": "/shared/model.joblib",
        "artifact_sha256": "a" * 64,
    }
    monkeypatch.setattr(provider, "_fetch_metadata", lambda: metadata)
    monkeypatch.setattr(
        ModelRuntime,
        "load",
        classmethod(lambda cls, **_kwargs: runtime),
    )

    assert provider.current() is runtime

    provider._checked_at = 0.0
    monkeypatch.setattr(
        provider,
        "_fetch_metadata",
        lambda: (_ for _ in ()).throw(
            httpx.ConnectError("training unavailable")
        ),
    )
    assert provider.current() is runtime
