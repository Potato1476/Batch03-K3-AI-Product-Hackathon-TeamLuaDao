"""Đo L5 trên hội thoại thật trong CHAN-Dataset.

Positive: kịch bản chiếm tài khoản mạng xã hội / mạo danh người quen vay tiền.
Negative: hội thoại hợp lệ trong 02_Negative — báo nhầm ở đây đắt hơn bỏ sót,
vì người dùng mất niềm tin vào cảnh báo.

Chạy:
    .venv/bin/chan-evaluate-thread --dataset repo/CHAN-Dataset \\
        --output repo/eval/l5-thread-results.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .thread import ThreadMessage, analyze_thread

TAKEOVER_SCENARIOS = {"Hacked_FB", "Hacked_Zalo", "Relative_Borrow"}


def to_thread(record: dict[str, Any]) -> list[ThreadMessage]:
    """scammer/victim trong dataset ↔ contact/user trong L5."""
    return [
        ThreadMessage(
            sender="user" if message.get("sender") == "victim" else "contact",
            text=(message.get("text") or "").strip(),
        )
        for message in record.get("messages", [])
        if (message.get("text") or "").strip()
    ]


def load(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(root.rglob("conv_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict) and payload.get("messages"):
            payload["_path"] = str(path.relative_to(root))
            records.append(payload)
    return records


def evaluate(records: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [r for r in records if r.get("scenario") in TAKEOVER_SCENARIOS]
    negatives = [r for r in records if r.get("source_type") is None]

    signal_counts: Counter[str] = Counter()
    insufficient = 0
    warned = 0
    positive_rows = []
    for record in positives:
        result = analyze_thread(to_thread(record))
        if result.insufficient_history:
            insufficient += 1
        for signal in result.thread_signals:
            signal_counts[signal.code] += 1
        if result.risk in {"high", "medium"}:
            warned += 1
        positive_rows.append(
            {
                "conversation_id": record.get("conversation_id"),
                "scenario": record.get("scenario"),
                "source": record.get("source"),
                "risk": result.risk,
                "signals": [s.code for s in result.thread_signals],
                "insufficient_history": result.insufficient_history,
            }
        )

    false_alarms = []
    negative_warned = 0
    for record in negatives:
        result = analyze_thread(to_thread(record))
        if result.risk in {"high", "medium"}:
            negative_warned += 1
            if len(false_alarms) < 20:
                false_alarms.append(
                    {
                        "conversation_id": record.get("conversation_id"),
                        "path": record["_path"],
                        "risk": result.risk,
                        "signals": [s.code for s in result.thread_signals],
                    }
                )

    return {
        "positives": len(positives),
        "negatives": len(negatives),
        "takeover_recall": round(warned / len(positives), 4) if positives else 0.0,
        "legitimate_false_positive_rate": (
            round(negative_warned / len(negatives), 4) if negatives else 0.0
        ),
        "positives_without_enough_history": insufficient,
        "signal_hit_counts": dict(signal_counts.most_common()),
        "false_alarm_samples": false_alarms,
        "positive_rows": positive_rows[:50],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate L5 on real conversations.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = evaluate(load(args.dataset))
    report["evaluated_at"] = "2026-07-30"
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    printable = {k: v for k, v in report.items() if not isinstance(v, list)}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
