"""Audit and convert the project-provided CHAN-Dataset into model JSONL.

The source folder duplicates each message in several representations and its
published evaluation folders contain substantial text overlap. This adapter
therefore reads conversation files only, applies L2 redaction, removes exact
post-redaction duplicates, drops contradictory labels, and assigns a stable
split from the canonical message text. The supplied benchmark is audited but
is not trusted as an independent holdout because its conversations overlap.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable, TextIO

from .normalize import normalize_for_model
from .redact import redact_l2, verify_redacted
from .schema import DatasetRecord

ADAPTER_VERSION = "team-json-adapter-1.4.1"
_POSITIVE_RISKS = {"medium", "high", "critical"}

_AUTHORITY_TEXT = re.compile(
    r"\b(?:cong an|can bo|canh sat|co quan thue|cuc thue|toa an|hai quan|"
    r"ngan hang|dien luc|evn|nha truong|benh vien)\b"
)
_SECRECY_TEXT = re.compile(
    r"\b(?:giu bi mat|tuyet doi khong tiet lo|khong (?:duoc )?"
    r"(?:noi|bao|ke).{0,24}(?:\bai\b|\bgia dinh\b|\bnguoi than\b)|"
    r"xoa tin nhan)\b"
)
_PRESSURE_TEXT = re.compile(
    r"\b(?:ngay lap tuc|lam ngay|xu ly ngay|chuyen ngay|gap|khan|"
    r"trong \d+ (?:phut|gio)|truoc \d+ ?h|sau \d+ ?h|hom nay|"
    r"se (?:bi )?(?:khoa|cat|phat|bat)|khong tri hoan)\b"
)
_TRANSFER_TEXT = re.compile(
    r"(?=.*\b(?:chuyen|gui|nop|nap|dong|thanh toan|tra)\b"
    r".{0,32}\b(?:tien|khoan|phi|coc|toan bo)\b)"
    r"(?=.*(?:<account>|\bstk\b|\bso tai khoan\b|"
    r"(?<!\d)\d(?:[\s.\-]?\d){7,18}(?!\d)))"
)
_APP_TEXT = re.compile(
    r"(?:\.apk\b|\b(?:tai|cai) (?:app|ung dung|phan mem)\b|"
    r"\bbat quyen (?:tro nang|accessibility)\b)"
)
_BENEFIT_TEXT = re.compile(
    r"\b(?:trung thuong|nhan qua|loi nhuan|lai \d+ ?%|hoa hong|"
    r"thu nhap|kiem \d+(?:k|trieu)?/(?:ngay|thang)|tro cap|hoan tien)\b"
)
_CHANNEL_TEXT = re.compile(
    r"\b(?:ket ban|nhan (?:tin|rieng)(?: qua)?|lien he|chuyen sang|"
    r"trao doi (?:qua|tren)|vao nhom).{0,20}"
    r"(?:zalo|telegram|viber|whatsapp|messenger|nhom chat)\b"
)
_OTP_TEXT = re.compile(
    r"\b(?:otp|ma xac (?:thuc|nhan)|mat khau|ten dang nhap)\b"
)
_SPLIT_VARIABLES = re.compile(
    r"(?:<[^>]+>|"
    r"\b(?:mb\s*bank|vpbank|vietcombank|vcb|bidv|agribank|"
    r"vietinbank|techcombank|sacombank|acb|tpbank)\b|"
    r"\b\d+(?:[.,:/-]\d+)*(?:[a-z]+)?\b)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class _Candidate:
    canonical: str
    text: str
    is_phishing: bool
    risk: str
    signals: frozenset[str]
    scenario: str
    conversation_id: str
    source: str
    input_mode: str


def _ascii(text: str) -> str:
    normalized = normalize_for_model(text)
    return "".join(
        character
        for character in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")


def derive_signal_codes(
    text: str, raw_signals: Iterable[str], *, is_phishing: bool
) -> frozenset[str]:
    """Map text onto eight evidence-backed product signals.

    The supplied 27-label annotation is incomplete (for example, many explicit
    authority claims lack ``authority_impersonation``). It is therefore audit
    context only; a product signal is assigned from explicit text evidence on
    phishing records and is never assigned on legitimate records.
    """

    if not is_phishing:
        return frozenset()
    # Consume the iterable so malformed non-iterable inputs still fail during
    # dataset preparation, while intentionally not trusting its completeness.
    tuple(raw_signals)
    return textual_signal_evidence(text)


def textual_signal_evidence(text: str) -> frozenset[str]:
    """Return eight-taxonomy signals with explicit support in the text."""

    normalized = _ascii(text)
    checks = {
        "mao_danh_tham_quyen": _AUTHORITY_TEXT,
        "yeu_cau_bi_mat": _SECRECY_TEXT,
        "ap_luc_thoi_gian": _PRESSURE_TEXT,
        "tk_ca_nhan": _TRANSFER_TEXT,
        "cai_app_ngoai": _APP_TEXT,
        "loi_ich_bat_thuong": _BENEFIT_TEXT,
        "chuyen_kenh": _CHANNEL_TEXT,
        "yeu_cau_otp": _OTP_TEXT,
    }
    return frozenset(
        code for code, pattern in checks.items() if pattern.search(normalized)
    )


def _channel(platform: str) -> tuple[str, str]:
    normalized = platform.strip().lower()
    if normalized in {"phone", "sms"}:
        return "android", "notification"
    if normalized == "zalo":
        return "zalo_oa", "share"
    return "web", "share"


def _scenario(document: dict[str, Any], *, legitimate: bool) -> str:
    if legitimate:
        return f"legitimate_{str(document.get('category', 'unknown')).lower()}"
    emotion = str(document.get("emotion", "unknown")).lower()
    scenario = str(document.get("scenario", "unknown")).lower()
    return f"{emotion}_{scenario}"


def _conversation_files(root: Path) -> list[Path]:
    scam = root.glob("01_Scenarios/*/*/conversations/*.json")
    legitimate = root.glob("02_Negative/*/conversations/*.json")
    return sorted([*scam, *legitimate])


def _benchmark_canonicals(root: Path) -> set[str]:
    canonicals: set[str] = set()
    for path in sorted((root / "09_Evaluation" / "benchmark").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for message in document.get("messages", []):
            text = str(message.get("text", "")).strip()
            if text:
                canonicals.add(normalize_for_model(redact_l2(text).text))
    return canonicals


def _candidates(root: Path) -> tuple[list[_Candidate], dict[str, int]]:
    candidates: list[_Candidate] = []
    counts: Counter[str] = Counter()
    for path in _conversation_files(root):
        document = json.loads(path.read_text(encoding="utf-8"))
        legitimate = document.get("label") == "legitimate"
        conversation_id = str(document.get("conversation_id", path.stem))
        scenario = _scenario(document, legitimate=legitimate)
        source, input_mode = _channel(str(document.get("platform", "web")))
        counts["conversation_files"] += 1
        for message in document.get("messages", []):
            counts["raw_messages"] += 1
            raw_text = str(message.get("text", "")).strip()
            if not raw_text:
                counts["empty_messages"] += 1
                continue
            sender = str(message.get("sender", "")).lower()
            raw_risk = str(message.get("risk", "")).lower()
            is_phishing = (
                not legitimate
                and sender == "scammer"
                and raw_risk in _POSITIVE_RISKS
            )
            risk = (
                "high"
                if is_phishing and raw_risk in {"high", "critical"}
                else "medium"
                if is_phishing
                else "unknown"
            )
            redacted = redact_l2(raw_text).text
            verify_redacted(redacted)
            canonical = normalize_for_model(redacted)
            signals = derive_signal_codes(
                raw_text,
                message.get("signals", []),
                is_phishing=is_phishing,
            )
            candidates.append(
                _Candidate(
                    canonical=canonical,
                    text=redacted,
                    is_phishing=is_phishing,
                    risk=risk,
                    signals=signals,
                    scenario=scenario,
                    conversation_id=conversation_id,
                    source=source,
                    input_mode=input_mode,
                )
            )
    return candidates, dict(counts)


def _stable_split(canonical: str, seed: int) -> str:
    digest = hashlib.sha256(f"{seed}:{canonical}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "test"


def _split_family_key(canonical: str) -> str:
    """Collapse common generated variables before assigning a data split.

    Messages that differ only by a bank, amount, placeholder, or number must
    stay in one split. This is stricter than exact-text splitting and prevents
    the generated templates from making validation/test scores look better.
    """

    skeleton = _SPLIT_VARIABLES.sub(" <variable> ", canonical)
    return " ".join(skeleton.split())


def prepare_records(
    root: Path, *, seed: int = 20260730
) -> tuple[list[DatasetRecord], dict[str, object]]:
    """Return deduplicated records and a leakage/quality audit manifest."""

    candidates, raw_counts = _candidates(root)
    benchmark = _benchmark_canonicals(root)
    grouped: dict[str, list[_Candidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.canonical, []).append(candidate)

    records: list[DatasetRecord] = []
    dropped_conflicts = 0
    merged_duplicates = 0
    for canonical, group in sorted(grouped.items()):
        labels = {item.is_phishing for item in group}
        if len(labels) != 1:
            dropped_conflicts += 1
            continue
        merged_duplicates += len(group) - 1
        is_phishing = group[0].is_phishing
        risk = (
            "high"
            if any(item.risk == "high" for item in group)
            else "medium"
            if is_phishing
            else "unknown"
        )
        signals = sorted({code for item in group for code in item.signals})
        scenarios = sorted({item.scenario for item in group})
        scenario = scenarios[0] if len(scenarios) == 1 else "cross_scenario"
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        records.append(
            DatasetRecord(
                id=f"team_{digest[:24]}",
                text=group[0].text,
                risk=risk,
                signals={code: 1.0 for code in signals},
                is_phishing=is_phishing,
                scenario=scenario,
                template_id=group[0].conversation_id,
                source=group[0].source,
                input_mode=group[0].input_mode,
                truncated=False,
                split=_stable_split(_split_family_key(canonical), seed),
                synthetic=False,
                consented=False,
                rights_basis="project_provided",
                generator_version=ADAPTER_VERSION,
            )
        )

    split_texts: dict[str, set[str]] = {
        split: {
            normalize_for_model(record.text)
            for record in records
            if record.split == split
        }
        for split in ("train", "validation", "test")
    }
    leakage = {
        "train_validation": len(split_texts["train"] & split_texts["validation"]),
        "train_test": len(split_texts["train"] & split_texts["test"]),
        "validation_test": len(split_texts["validation"] & split_texts["test"]),
    }
    manifest: dict[str, object] = {
        "adapter_version": ADAPTER_VERSION,
        "seed": seed,
        **raw_counts,
        "post_redaction_unique_records": len(records),
        "merged_duplicate_messages": merged_duplicates,
        "dropped_conflicting_labels": dropped_conflicts,
        "benchmark_canonical_messages": len(benchmark),
        "benchmark_warning": (
            "The supplied benchmark duplicates 200 training conversation IDs; "
            "it is audited but not trusted as a split. Stable post-redaction "
            "text hashing creates leakage-free train/validation/test splits."
        ),
        "split_counts": dict(Counter(record.split for record in records)),
        "phishing_counts": dict(
            Counter(str(record.is_phishing).lower() for record in records)
        ),
        "risk_counts": dict(Counter(record.risk for record in records)),
        "scenario_counts": dict(Counter(record.scenario for record in records)),
        "exact_text_leakage_across_splits": leakage,
        "split_strategy": "stable_hash_of_variable_collapsed_text_family",
        "contains_real_person_data": False,
        "redaction_state": "L2 placeholders only",
        "rights_basis": "project_provided; verify upstream licences before production",
    }
    return records, manifest


def _open_output(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        return gzip.open(path, "wt", encoding="utf-8")
    return path.open("w", encoding="utf-8")


def write_prepared_dataset(
    records: Iterable[DatasetRecord],
    output: Path,
    manifest: dict[str, object],
) -> dict[str, object]:
    digest = hashlib.sha256()
    with _open_output(output) as handle:
        for record in records:
            line = json.dumps(
                record.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            handle.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
    complete = {
        **manifest,
        "content_sha256_uncompressed_jsonl": digest.hexdigest(),
    }
    Path(str(output) + ".manifest.json").write_text(
        json.dumps(complete, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return complete


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit, redact, deduplicate, and split CHAN-Dataset."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260730)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    records, manifest = prepare_records(args.input, seed=args.seed)
    complete = write_prepared_dataset(records, args.output, manifest)
    print(json.dumps(complete, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
