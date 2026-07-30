"""Unit tests for the pieces that HTTP tests cannot reach directly."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chan_ml.constants import SIGNAL_CODES

from chan_api.hotlines import HotlineDirectory
from chan_api.l3.base import (
    Classification,
    SignalScore,
    apply_local_signal_boosts,
    merge,
)
from chan_api.l3.llm import LlmClassificationError, _parse_signals
from chan_api.l3.similarity import NullSimilarity, SimilarityResult
from chan_api.ratelimit import InProcessBackend, RateLimiter
from chan_api.rules import MAX_SINGLE_BOOST, MAX_TOTAL_BOOST, RuleBundleStore

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


# --- Rule Bundle ------------------------------------------------------------


@pytest.fixture
def bundle():  # noqa: ANN201
    return RuleBundleStore(RULES_DIR / "bundle.json").get()


def test_bundle_parses_and_declares_a_version(bundle) -> None:
    assert bundle.version.startswith("rb-")
    assert len(bundle.etag) == 32


def test_default_config_finds_the_bundle_in_a_checkout(monkeypatch) -> None:
    """Running from source with no env vars must locate codebase/rules.

    Regression: the repo-relative fallback was one directory too high, so every
    /v1/analyze call failed at runtime while the tests passed — they injected the
    path explicitly and never exercised the default.
    """
    from chan_api.config import AppConfig

    for name in ("CHAN_RULES_DIR", "CHAN_L3_PROVIDER", "CHAN_OCR_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    config = AppConfig.from_environment()
    assert config.bundle_path.exists(), f"{config.bundle_path} does not exist"
    assert config.hotlines_path.exists()
    assert config.rules_dir.resolve() == RULES_DIR.resolve()


def test_bundle_maps_local_signals_onto_the_taxonomy(bundle) -> None:
    boosts = bundle.boosts_for(("apk_link",))
    assert set(boosts) <= set(SIGNAL_CODES)
    assert boosts["cai_app_ngoai"] > 0


def test_a_single_local_signal_boost_is_capped(bundle) -> None:
    for name in bundle.local_signal_names:
        for code, boost in bundle.boosts_for((name,)).items():
            assert boost <= MAX_SINGLE_BOOST, f"{name} -> {code} exceeds the cap"


def test_total_local_boost_is_capped(bundle) -> None:
    """A modified client must not be able to drive the score by itself."""
    everything = tuple(bundle.local_signal_names)
    assert sum(bundle.boosts_for(everything).values()) <= MAX_TOTAL_BOOST + 1e-9


def test_unknown_local_signal_contributes_nothing(bundle) -> None:
    assert bundle.boosts_for(("no_such_signal",)) == {}


def test_repeated_local_signal_counts_once(bundle) -> None:
    once = bundle.boosts_for(("apk_link",))
    thrice = bundle.boosts_for(("apk_link", "apk_link", "apk_link"))
    assert once == thrice


def test_bundle_reloads_when_the_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps({"bundle_version": "rb-1"}), encoding="utf-8")
    store = RuleBundleStore(path)
    assert store.get().version == "rb-1"

    import os
    import time

    time.sleep(0.01)
    path.write_text(json.dumps({"bundle_version": "rb-2"}), encoding="utf-8")
    os.utime(path, (time.time() + 1, time.time() + 1))
    assert store.get().version == "rb-2"


def test_bundle_without_a_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="missing_version"):
        RuleBundleStore(path).get()


def test_every_bundle_regex_compiles(bundle) -> None:
    """A broken pattern here would break L1 on both clients at once."""
    import re

    patterns: list[str] = []
    otp = bundle.payload["l1"]["otp_block"]["patterns"]
    patterns.extend(otp)
    for rule in bundle.payload["l1"]["local_signals"].values():
        patterns.extend(
            pattern
            for pattern in rule.get("patterns", [])
            if not pattern.startswith("__")
        )
    patterns.extend(bundle.payload["l1"]["identifier_extraction"].values())
    for pattern in patterns:
        re.compile(pattern)


def test_bundle_signal_targets_are_all_real_codes(bundle) -> None:
    for name, rule in bundle.payload["l1"]["local_signals"].items():
        target = rule.get("boost_signal")
        assert target is None or target in SIGNAL_CODES, name


# --- L3 merge / boosts ------------------------------------------------------


def _classification(**scores: float) -> Classification:
    return Classification(
        signals=tuple(
            SignalScore(code=code, confidence=value) for code, value in scores.items()
        ),
        provider="test",
        engine_version="test-1",
    )


def test_merge_takes_the_higher_confidence_per_signal() -> None:
    merged = merge(
        [
            _classification(mao_danh_tham_quyen=0.9, ap_luc_thoi_gian=0.2),
            _classification(mao_danh_tham_quyen=0.4, ap_luc_thoi_gian=0.8),
        ],
        provider="ensemble",
    )
    scores = merged.as_map()
    assert scores["mao_danh_tham_quyen"] == 0.9
    assert scores["ap_luc_thoi_gian"] == 0.8


def test_merge_keeps_the_evidence_of_the_winning_score() -> None:
    merged = merge(
        [
            Classification(
                signals=(SignalScore("tk_ca_nhan", 0.9, "tai khoan ca nhan"),),
                provider="a",
                engine_version="a-1",
            ),
            Classification(
                signals=(SignalScore("tk_ca_nhan", 0.3, "weaker"),),
                provider="b",
                engine_version="b-1",
            ),
        ],
        provider="ensemble",
    )
    assert merged.evidence_map()["tk_ca_nhan"] == "tai khoan ca nhan"


def test_merge_of_one_is_a_passthrough() -> None:
    single = _classification(chuyen_kenh=0.5)
    assert merge([single], provider="ensemble") is single


def test_merge_of_nothing_raises() -> None:
    with pytest.raises(ValueError):
        merge([], provider="ensemble")


def test_boosts_are_clamped_to_one() -> None:
    boosted = apply_local_signal_boosts(
        _classification(cai_app_ngoai=0.95), {"cai_app_ngoai": 0.3}
    )
    assert boosted.as_map()["cai_app_ngoai"] == 1.0


def test_boost_for_an_unknown_code_is_ignored() -> None:
    boosted = apply_local_signal_boosts(_classification(chuyen_kenh=0.1), {"nope": 0.5})
    assert "nope" not in boosted.as_map()


def test_signal_score_rejects_a_code_outside_the_taxonomy() -> None:
    with pytest.raises(ValueError, match="unknown signal code"):
        SignalScore(code="safe", confidence=1.0)


# --- LLM response parsing ---------------------------------------------------


def test_llm_evidence_must_be_a_real_quote() -> None:
    """§5: an invented quote is worse than none, so it drops below the line."""
    parsed = _parse_signals(
        {
            "signals": [
                {
                    "code": "mao_danh_tham_quyen",
                    "confidence": 0.95,
                    "evidence": "a phrase that was never in the message",
                }
            ]
        },
        "toi la can bo thue",
    )
    assert parsed[0].evidence == ""
    assert parsed[0].confidence <= 0.49


def test_llm_evidence_that_is_a_real_quote_survives() -> None:
    parsed = _parse_signals(
        {
            "signals": [
                {
                    "code": "mao_danh_tham_quyen",
                    "confidence": 0.95,
                    "evidence": "can bo thue",
                }
            ]
        },
        "toi la can bo thue",
    )
    assert parsed[0].evidence == "can bo thue"
    assert parsed[0].confidence == 0.95


def test_llm_codes_outside_the_taxonomy_are_discarded() -> None:
    parsed = _parse_signals(
        {
            "signals": [
                {"code": "safe", "confidence": 1.0, "evidence": ""},
                {"code": "chuyen_kenh", "confidence": 0.7, "evidence": ""},
            ]
        },
        "chuyen sang telegram",
    )
    assert [signal.code for signal in parsed] == ["chuyen_kenh"]


def test_llm_confidence_is_clamped() -> None:
    parsed = _parse_signals(
        {"signals": [{"code": "chuyen_kenh", "confidence": 5.0, "evidence": ""}]},
        "abc",
    )
    assert parsed[0].confidence == 1.0


def test_llm_malformed_payload_raises() -> None:
    with pytest.raises(LlmClassificationError):
        _parse_signals({"signals": "not a list"}, "abc")
    with pytest.raises(LlmClassificationError):
        _parse_signals({"signals": [{"code": "nope"}]}, "abc")


# --- hotlines ---------------------------------------------------------------


def test_hotline_only_resolves_for_an_impersonation_signal() -> None:
    directory = HotlineDirectory(RULES_DIR / "hotlines.json")
    assert directory.resolve("co quan thue", signal_codes=frozenset()) is None
    assert (
        directory.resolve("co quan thue", signal_codes=frozenset({"chuyen_kenh"}))
        is None
    )


def test_hotline_matches_the_claimed_authority() -> None:
    directory = HotlineDirectory(RULES_DIR / "hotlines.json")
    hotline = directory.resolve(
        "toi la can bo cuc thue, anh no thue",
        signal_codes=frozenset({"mao_danh_tham_quyen"}),
    )
    assert hotline is not None
    assert "Thuế" in hotline.name


def test_hotline_falls_back_to_the_default(tmp_path: Path) -> None:
    directory = HotlineDirectory(RULES_DIR / "hotlines.json")
    hotline = directory.resolve(
        "mot co quan nao do khong ro",
        signal_codes=frozenset({"mao_danh_tham_quyen"}),
    )
    assert hotline is not None and hotline.number == "156"


def test_missing_hotline_file_is_not_fatal(tmp_path: Path) -> None:
    directory = HotlineDirectory(tmp_path / "absent.json")
    assert (
        directory.resolve("abc", signal_codes=frozenset({"mao_danh_tham_quyen"}))
        is None
    )


# --- rate limiting ----------------------------------------------------------


def test_limiter_allows_up_to_the_limit_then_blocks() -> None:
    limiter = RateLimiter(InProcessBackend())
    assert all(
        limiter.check(scope="t", identity="d", limit=3, window_seconds=60)
        for _ in range(3)
    )
    assert not limiter.check(scope="t", identity="d", limit=3, window_seconds=60)


def test_limiter_separates_identities_and_scopes() -> None:
    limiter = RateLimiter(InProcessBackend())
    assert limiter.check(scope="a", identity="one", limit=1)
    assert not limiter.check(scope="a", identity="one", limit=1)
    assert limiter.check(scope="a", identity="two", limit=1)
    assert limiter.check(scope="b", identity="one", limit=1)


# --- similarity -------------------------------------------------------------


def test_null_similarity_returns_zero() -> None:
    """With no embeddings, the β term must vanish rather than bias the score."""
    import asyncio

    result = asyncio.run(NullSimilarity().score("abc"))
    assert result == SimilarityResult()
    assert result.similarity_max == 0.0
    assert not result.available
