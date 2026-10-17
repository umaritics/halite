"""Measure token usage for at most ten fresh conflict-classification calls."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from services.conflict_engine import _CLASSIFICATION_SYSTEM_PROMPT, _parse_classification


PAIRS = (
    ("AALA202501093468", "AALA202501063468"),
    ("AALA202501074549", "AALA202501034549"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--max-calls", type=int, default=10, choices=range(1, 11))
    args = parser.parse_args()
    if not settings.GROQ_API_KEY:
        raise SystemExit("GROQ_API_KEY is not configured")

    with open(args.corpus, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["OperatorControlNumber"]: row for row in rows}

    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    measurements = []
    call = 0
    error = None
    for new_id, prior_id in PAIRS:
        new, prior = by_id[new_id], by_id[prior_id]
        prompt = (
            f"NEW RECORD (occurred_at={new.get('DifficultyDate', '?')}):\n"
            f"{new.get('Discrepancy', '')[:800]}\n\n"
            f"PRIOR RECORD (occurred_at={prior.get('DifficultyDate', '?')}):\n"
            f"{prior.get('Discrepancy', '')[:800]}"
        )
        for _ in range(5):
            if call >= args.max_calls:
                break
            call += 1
            try:
                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": _CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=800,
                    temperature=0.3,
                )
                parsed = _parse_classification(response.choices[0].message.content)
                usage = response.usage
                measurements.append({
                    "pair": f"{new_id}/{prior_id}",
                    "label": parsed["label"],
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                })
            except Exception as exc:
                error = str(exc)
                break
        if error or call >= args.max_calls:
            break

    totals = Counter()
    for row in measurements:
        totals.update({key: row[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")})
    labels_by_pair = {}
    for pair in {row["pair"] for row in measurements}:
        labels_by_pair[pair] = dict(Counter(row["label"] for row in measurements if row["pair"] == pair))
    print(json.dumps({
        "model": settings.GROQ_MODEL,
        "calls_attempted": call,
        "calls_completed": len(measurements),
        "error": error,
        "totals": dict(totals),
        "per_call_average": {
            key: round(totals[key] / len(measurements), 2) if measurements else None
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        "vote_labels": labels_by_pair,
        "calls": measurements,
    }, indent=2))


if __name__ == "__main__":
    main()
