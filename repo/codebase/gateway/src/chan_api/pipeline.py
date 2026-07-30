"""The L2 → lookup → L3 → L4 pipeline for /v1/analyze.

Kept out of the router so each stage is unit-testable without HTTP, and so the
ordering that the invariants depend on is stated in one place:

    L2 redact  →  OTP short-circuit (I1)  →  blocklist  →  L3  →  L4  →  shape

The risk decision is never made here. It is delegated to
``chan_ml.policy.aggregate_risk``, the same deterministic function the model and
the training API use, so a threshold can only be changed in one place (§6).
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
from dataclasses import dataclass, field

from chan_ml.constants import SIGNAL_DECISION_THRESHOLD, SIGNAL_CODES
from chan_ml.normalize import normalize_for_model
from chan_ml.policy import aggregate_risk
from chan_ml.redact import RedactionResult, redact_l2

from .hotlines import Hotline, HotlineDirectory
from .l3.base import Classification, SignalScore, apply_local_signal_boosts
from .l3.similarity import SimilarityResult
from .repository import GatewayRepository
from .rules import RuleBundle

#: Ordering for display and for choosing which signals drive the explanation.
_SIGNAL_PRIORITY = {
    "yeu_cau_otp": 8,
    "yeu_cau_bi_mat": 7,
    "cai_app_ngoai": 6,
    "tk_ca_nhan": 5,
    "mao_danh_tham_quyen": 4,
    "ap_luc_thoi_gian": 3,
    "loi_ich_bat_thuong": 2,
    "chuyen_kenh": 1,
}

_EXPLANATIONS = {
    "mao_danh_tham_quyen": "Tin nhắn tự nhận là cơ quan hoặc tổ chức có thẩm quyền.",
    "yeu_cau_bi_mat": "Người gửi yêu cầu giữ bí mật với gia đình.",
    "ap_luc_thoi_gian": "Người gửi thúc ép phải làm ngay.",
    "tk_ca_nhan": "Tin nhắn yêu cầu chuyển tiền vào tài khoản cá nhân.",
    "cai_app_ngoai": "Tin nhắn yêu cầu cài ứng dụng ngoài cửa hàng chính thức.",
    "loi_ich_bat_thuong": "Tin nhắn hứa một khoản lợi ích bất thường.",
    "chuyen_kenh": "Người gửi muốn chuyển sang một kênh liên lạc riêng.",
    "yeu_cau_otp": "Người gửi yêu cầu cung cấp mã xác nhận.",
}

_QUESTIONS = {
    "mao_danh_tham_quyen": "Tôi có thể tự gọi số chính thức của cơ quan để kiểm tra không?",
    "yeu_cau_bi_mat": "Tại sao việc này lại không được nói với người thân?",
    "ap_luc_thoi_gian": "Tại sao tôi phải làm ngay mà không có thời gian kiểm tra?",
    "tk_ca_nhan": "Tại sao tiền lại chuyển vào tài khoản cá nhân?",
    "cai_app_ngoai": "Ứng dụng này có trên cửa hàng chính thức không?",
    "loi_ich_bat_thuong": "Tại sao tôi nhận được lợi ích này khi chưa đăng ký?",
    "chuyen_kenh": "Tại sao không trao đổi qua kênh chính thức?",
    "yeu_cau_otp": "Tại sao anh/chị cần mã xác nhận chỉ mình tôi được biết?",
}

_OTP_EXPLANATION = (
    "Tin nhắn này đang hỏi mã xác nhận của bạn. "
    "Không ai có quyền hỏi mã đó — kể cả ngân hàng hay công an. "
    "Đừng đọc mã cho bất kỳ ai."
)

_BLOCKLIST_EXPLANATION = (
    "Số tài khoản trong tin nhắn này đã bị người khác báo cáo là lừa đảo. "
    "Đừng chuyển tiền."
)

_TRUNCATED_NOTE = (
    " Nội dung có thể đã bị cắt ngắn, "
    "hãy mở ứng dụng và gửi lại bản đầy đủ để kiểm tra chính xác hơn."
)


@dataclass(frozen=True)
class AnalysisOutcome:
    analysis_id: str
    risk: str
    score: float
    signals: tuple[dict[str, object], ...]
    explanation: str
    questions: tuple[str, ...]
    verified_hotline: Hotline | None
    actions: tuple[str, ...]
    engine_version: str
    rule_bundle_version: str
    text_sha256: bytes
    blocklist_match: bool
    #: Signals stripped of evidence, for persistence (I2).
    storable_signals: tuple[dict[str, object], ...] = field(default=())


def new_analysis_id() -> str:
    return f"an_{secrets.token_hex(6)}"


def text_digest(text: str) -> bytes:
    return hashlib.sha256(normalize_for_model(text).encode("utf-8")).digest()


async def check_blocklist(
    repository: GatewayRepository, redaction: RedactionResult
) -> bool:
    """§6 hard override: a recipient account already reported means high risk.

    These hashes are derived server-side from the submitted text, so this is not
    a user lookup and I4 does not apply — the user did not ask us anything about
    a value they chose to keep private.
    """
    from starlette.concurrency import run_in_threadpool

    if not redaction.all_hashes:
        return False

    def _check() -> bool:
        return (
            repository.blocklist_contains("account", redaction.account_hashes)
            or repository.blocklist_contains("phone", redaction.phone_hashes)
            or repository.blocklist_contains("url", redaction.url_hashes)
        )

    try:
        return await run_in_threadpool(_check)
    except Exception:  # noqa: BLE001 - a lookup outage must not fail analysis
        return False


def otp_outcome(
    *,
    bundle: RuleBundle,
    engine_version: str,
    truncated: bool,
    text_sha256: bytes,
) -> AnalysisOutcome:
    """I1: an OTP request is decided without the message reaching a model."""
    signal = {
        "code": "yeu_cau_otp",
        "confidence": 1.0,
        # No evidence: quoting it back would echo the digits we just removed.
        "evidence": "",
    }
    policy = aggregate_risk({"yeu_cau_otp": 1.0})
    explanation = _OTP_EXPLANATION + (_TRUNCATED_NOTE if truncated else "")
    return AnalysisOutcome(
        analysis_id=new_analysis_id(),
        risk=policy.risk,
        score=policy.score,
        signals=(signal,),
        explanation=explanation,
        questions=(_QUESTIONS["yeu_cau_otp"],),
        verified_hotline=None,
        actions=("report", "share_to_guardian"),
        engine_version=engine_version,
        rule_bundle_version=bundle.version,
        text_sha256=text_sha256,
        blocklist_match=False,
        storable_signals=({"code": "yeu_cau_otp", "confidence": 1.0},),
    )


def build_outcome(
    *,
    redacted_text: str,
    classification: Classification,
    similarity: SimilarityResult,
    similarity_beta: float,
    blocklist_match: bool,
    bundle: RuleBundle,
    hotlines: HotlineDirectory,
    truncated: bool,
    text_sha256: bytes,
    evidence: dict[str, str] | None = None,
) -> AnalysisOutcome:
    """L4 aggregation plus response shaping (§6, §7)."""
    confidences = classification.as_map()
    evidence_map = {**classification.evidence_map(), **(evidence or {})}

    policy = aggregate_risk(
        confidences,
        similarity_max=similarity.similarity_max,
        similarity_beta=similarity_beta,
        blocklist_match=blocklist_match,
    )

    reported = [
        {
            "code": code,
            "confidence": round(confidences.get(code, 0.0), 4),
            "evidence": (evidence_map.get(code) or "")[:240],
        }
        for code in SIGNAL_CODES
        if confidences.get(code, 0.0) >= SIGNAL_DECISION_THRESHOLD
    ]
    reported.sort(
        key=lambda item: (
            _SIGNAL_PRIORITY[str(item["code"])],
            float(item["confidence"]),  # type: ignore[arg-type]
        ),
        reverse=True,
    )

    codes = frozenset(str(item["code"]) for item in reported)

    if policy.risk == "unknown":
        # I6: the neutral label, never reassurance. No signals are listed
        # because none crossed the reporting line.
        reported = []
        codes = frozenset()
        explanation = "Chưa phát hiện dấu hiệu."
    elif blocklist_match:
        explanation = _BLOCKLIST_EXPLANATION
    else:
        leading = reported[:1] if reported and reported[0]["code"] == "yeu_cau_otp" else reported[:3]
        explanation = " ".join(
            _EXPLANATIONS[str(item["code"])] for item in leading
        ) or "Cần kiểm tra thêm trước khi làm theo."

    if truncated and policy.risk != "unknown":
        explanation += _TRUNCATED_NOTE

    asked = reported[:1] if reported and reported[0]["code"] == "yeu_cau_otp" else reported[:2]
    questions = tuple(_QUESTIONS[str(item["code"])] for item in asked)

    hotline = (
        hotlines.resolve(redacted_text, signal_codes=codes)
        if policy.risk != "unknown"
        else None
    )

    actions: tuple[str, ...] = ()
    if policy.risk != "unknown":
        actions = ("report", "share_to_guardian")
        if "tk_ca_nhan" in codes or blocklist_match:
            actions += ("lookup_account",)

    return AnalysisOutcome(
        analysis_id=new_analysis_id(),
        risk=policy.risk,
        score=policy.score,
        signals=tuple(reported),
        explanation=explanation,
        questions=questions,
        verified_hotline=hotline,
        actions=actions,
        engine_version=classification.engine_version,
        rule_bundle_version=bundle.version,
        text_sha256=text_sha256,
        blocklist_match=blocklist_match,
        # I2: evidence is returned to the client and dropped before storage.
        storable_signals=tuple(
            {"code": item["code"], "confidence": item["confidence"]}
            for item in reported
        ),
    )


async def gather_signals(
    *,
    classifier,  # noqa: ANN001 - SignalClassifier
    similarity,  # noqa: ANN001 - has .score()
    redacted_text: str,
    local_boosts: dict[str, float],
) -> tuple[Classification, SimilarityResult]:
    """Run L3 and the similarity probe concurrently (§5: two parallel sources)."""
    classification_task = asyncio.create_task(classifier.classify(redacted_text))
    similarity_task = asyncio.create_task(similarity.score(redacted_text))
    classification, similarity_result = await asyncio.gather(
        classification_task, similarity_task
    )
    return apply_local_signal_boosts(classification, local_boosts), similarity_result


def redact(text: str) -> RedactionResult:
    return redact_l2(text)
