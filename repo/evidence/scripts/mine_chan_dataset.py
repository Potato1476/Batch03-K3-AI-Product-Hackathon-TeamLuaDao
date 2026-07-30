"""Đếm trên CHAN-Dataset — bằng chứng chuẩn B cho spec.md §1.

Chạy:
    .venv/bin/python evidence/scripts/mine_chan_dataset.py \
        --dataset repo/CHAN-Dataset --output repo/evidence/mining-results.json

Tiêu chí đếm nằm hết trong file này để người ngoài nhóm chạy lại ra đúng số.
Không có bước thủ công nào ở giữa.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

#: Kịch bản chiếm tài khoản mạng xã hội rồi nhắn người quen vay tiền.
TAKEOVER_SCENARIOS = {"Hacked_FB", "Hacked_Zalo", "Relative_Borrow"}

#: Outcome trong dataset. "victim_transferred_money" = nạn nhân đã chuyển tiền.
LOSS_OUTCOME = "victim_transferred_money"


def load_conversations(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(root.rglob("conv_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict) and "messages" in payload:
            payload["_path"] = str(path.relative_to(root))
            records.append(payload)
    return records


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_source_type = Counter(record.get("source_type") or "negative" for record in records)
    by_source = Counter(record.get("source") or "negative" for record in records)
    by_scenario = Counter(record.get("scenario") or "negative" for record in records)
    by_outcome = Counter(record.get("outcome") or "unknown" for record in records)

    takeover = [r for r in records if r.get("scenario") in TAKEOVER_SCENARIOS]
    takeover_seed = [r for r in takeover if r.get("source_type") == "seed"]
    takeover_loss = [r for r in takeover if r.get("outcome") == LOSS_OUTCOME]

    scam = [r for r in records if r.get("source_type") in {"seed", "synthetic"}]
    scam_loss = [r for r in scam if r.get("outcome") == LOSS_OUTCOME]

    # Bao nhiêu hội thoại lừa đảo có ít nhất một lời hỏi tiền từ phía kẻ gian?
    money_words = ("chuyen", "chuyển", "tien", "tiền", "stk", "tài khoản", "tai khoan")
    with_money_ask = [
        record
        for record in scam
        if any(
            message.get("sender") == "scammer"
            and any(word in (message.get("text") or "").lower() for word in money_words)
            for message in record.get("messages", [])
        )
    ]

    lengths = [len(record.get("messages", [])) for record in records if record.get("messages")]
    return {
        "total_conversations": len(records),
        "total_messages": sum(lengths),
        "median_messages_per_conversation": sorted(lengths)[len(lengths) // 2] if lengths else 0,
        "by_source_type": dict(by_source_type.most_common()),
        "by_source": dict(by_source.most_common()),
        "by_scenario": dict(by_scenario.most_common()),
        "by_outcome": dict(by_outcome.most_common()),
        "scam_conversations": len(scam),
        "scam_ending_in_money_transferred": len(scam_loss),
        "scam_with_explicit_money_ask": len(with_money_ask),
        "account_takeover_conversations": len(takeover),
        "account_takeover_from_real_seed_sources": len(takeover_seed),
        "account_takeover_ending_in_money_transferred": len(takeover_loss),
    }


def sample_quotes(records: list[dict[str, Any]], limit: int = 6) -> list[dict[str, str]]:
    """Trích nguyên văn kèm ID để người chấm mở lại đúng file."""
    quotes = []
    for record in records:
        if record.get("scenario") not in TAKEOVER_SCENARIOS:
            continue
        if record.get("source_type") != "seed":
            continue
        for message in record.get("messages", []):
            text = (message.get("text") or "").strip()
            if message.get("sender") != "scammer" or len(text) < 40:
                continue
            if not any(word in text.lower() for word in ("chuyen", "chuyển", "tiền", "tien")):
                continue
            quotes.append(
                {
                    "conversation_id": record.get("conversation_id", ""),
                    "scenario": record.get("scenario", ""),
                    "source": record.get("source", ""),
                    "message_id": message.get("message_id", ""),
                    "path": record["_path"],
                    "text": text,
                }
            )
            break
        if len(quotes) >= limit:
            break
    return quotes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = load_conversations(args.dataset)
    report = {
        "counted_at": "2026-07-30",
        "dataset_root": str(args.dataset),
        "counting_rules": {
            "conversation": "mỗi file conv_*.json có khoá 'messages' là một hội thoại",
            "scam_vs_negative": "source_type in {seed, synthetic} là lừa đảo; thiếu source_type là hội thoại hợp lệ trong 02_Negative",
            "account_takeover": sorted(TAKEOVER_SCENARIOS),
            "loss_outcome": LOSS_OUTCOME,
            "money_ask": "tin của sender=scammer có chứa một trong: chuyen/chuyển/tien/tiền/stk/tài khoản",
        },
        "summary": summarise(records),
        "verbatim_examples": sample_quotes(records),
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
