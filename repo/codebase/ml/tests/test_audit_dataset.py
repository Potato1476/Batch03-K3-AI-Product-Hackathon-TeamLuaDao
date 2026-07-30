from dataclasses import replace
from pathlib import Path

from chan_ml.audit_dataset import audit_dataset
from chan_ml.schema import DatasetRecord
from chan_ml.team_dataset import write_prepared_dataset


def _record(identifier: str, *, phishing: bool, split: str) -> DatasetRecord:
    return DatasetRecord(
        id=identifier,
        text=(
            "Chuyển tiền vào STK <ACCOUNT> ngay."
            if phishing
            else "Lịch họp của nhóm vào sáng mai."
        ),
        risk="high" if phishing else "unknown",
        signals={"tk_ca_nhan": 1.0} if phishing else {},
        is_phishing=phishing,
        scenario="test",
        template_id=identifier,
        source="web",
        input_mode="manual",
        truncated=False,
        split=split,
        synthetic=False,
        rights_basis="project_provided",
    )


def test_audit_checks_every_record_and_passes_consistent_data(tmp_path: Path):
    records = [
        _record("p1", phishing=True, split="train"),
        _record("n1", phishing=False, split="train"),
        replace(
            _record("p-authority", phishing=True, split="train"),
            text="Công an thông báo hồ sơ đang bị điều tra.",
            signals={"mao_danh_tham_quyen": 1.0},
        ),
        replace(
            _record("p-secret", phishing=True, split="train"),
            text="Giữ bí mật, không được nói với gia đình.",
            signals={"yeu_cau_bi_mat": 1.0},
        ),
        replace(
            _record("p-pressure", phishing=True, split="train"),
            text="Làm ngay trong 2 giờ nếu không sẽ bị khóa.",
            signals={"ap_luc_thoi_gian": 1.0},
        ),
        replace(
            _record("p-app", phishing=True, split="train"),
            text="Tải app lạ và bật quyền trợ năng.",
            signals={"cai_app_ngoai": 1.0},
        ),
        replace(
            _record("p-reward", phishing=True, split="train"),
            text="Bạn đã trúng thưởng một phần quà.",
            signals={"loi_ich_bat_thuong": 1.0},
        ),
        replace(
            _record("p-channel", phishing=True, split="train"),
            text="Liên hệ qua Telegram để trao đổi.",
            signals={"chuyen_kenh": 1.0},
        ),
        replace(
            _record("p-otp", phishing=True, split="train"),
            text="Gửi mã OTP xác thực cho tôi.",
            signals={"yeu_cau_otp": 1.0},
        ),
        replace(
            _record("p2", phishing=True, split="validation"),
            text="Nộp phí vào số tài khoản <ACCOUNT>.",
        ),
        replace(
            _record("n2", phishing=False, split="test"),
            text="Hẹn gặp bác tại cửa hàng chiều thứ hai.",
        ),
    ]
    path = tmp_path / "dataset.jsonl.gz"
    write_prepared_dataset(records, path, {})

    result = audit_dataset(path)

    assert result["records_checked"] == 11
    assert result["passed"] is True


def test_audit_rejects_signal_without_text_evidence(tmp_path: Path):
    records = [
        replace(
            _record("p1", phishing=True, split="train"),
            text="Xin chào bạn.",
        ),
        _record("n1", phishing=False, split="validation"),
    ]
    path = tmp_path / "dataset.jsonl.gz"
    write_prepared_dataset(records, path, {})

    result = audit_dataset(path)

    assert result["passed"] is False
    assert any(
        item["reason"] == "signal_without_text_evidence:tk_ca_nhan"
        for item in result["errors"]
    )
