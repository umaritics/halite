"""Measure conflict-analysis candidate cost and cached partial-run quality.

This script is read-only outside its ephemeral in-memory graph.  It never calls
an LLM: a cache miss aborts the 103-record replay rather than fabricating data.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.maintenance_agent import MaintenanceAgent
from domains.registry import get_adapter
from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from services.conflict_engine import find_candidate_pairs, process_record
from services.conflict_screen import text_overlap_features


ANSWER_KEY = re.compile(
    r"SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*[A-Z0-9]{6,}\s*\)?", re.I
)
WORDS = re.compile(r"[A-Z0-9]+")
STOP = {
    "THIS", "THAT", "WITH", "FROM", "WERE", "WAS", "HAVE", "HAS", "HAD",
    "THE", "AND", "FOR", "OF", "TO", "IN", "ON", "AT", "IS", "A", "AN",
    "AIRCRAFT", "FOUND", "DURING", "INSPECTION", "REPLACED", "REPAIR",
}


def _norm(value) -> str:
    return " ".join(str(value or "").upper().split())


def _tokens(text: str) -> set[str]:
    # The author citation is an answer key and is removed before tokenization.
    clean = ANSWER_KEY.sub("", text or "")
    return {word for word in WORDS.findall(clean.upper()) if len(word) >= 4 and word not in STOP}


def tight_gate(new: dict, prior: dict) -> bool:
    """Offline option A only; production pairing is intentionally unchanged."""
    component_match = any(
        _norm(new.get(field)) and _norm(new.get(field)) == _norm(prior.get(field))
        for field in ("part_name", "jasc_code", "part_location")
    )
    left, right = _tokens(new.get("text", "")), _tokens(prior.get("text", ""))
    shared = left & right
    overlap = len(shared) / len(left | right) if left | right else 0.0
    return component_match or (len(shared) >= 2 and overlap >= 0.20)


class CacheOnlyGroq:
    model = "qwen/qwen3.8-27b"
    is_live = True

    def extract_json(self, *args, **kwargs):
        raise RuntimeError("cache miss: live calls are forbidden in measurement replay")


def _bucket(count: int) -> str:
    if count <= 2:
        return str(count)
    if count <= 5:
        return "3-5"
    return "6+"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--partial", type=int, default=103)
    args = parser.parse_args()

    repo = GraphRepository(MemoryGraphStore())
    ingest = MaintenanceAgent(repo, None).run({"csv_path": args.corpus})
    records = sorted(
        repo.list_service_records(),
        key=lambda row: (row.get("occurred_at", ""), row.get("record_id", "")),
    )
    by_id = {row["record_id"]: row for row in records}

    raw_candidates = {}
    capped_candidates = {}
    tight_candidates = {}
    cascade_candidates = {}
    histogram = Counter()
    for index, record in enumerate(records, 1):
        raw = find_candidate_pairs(repo, record["record_id"], max_candidates=10_000)
        capped = raw[:25]
        tight = [item for item in raw if tight_gate(record, item["record"])]
        enriched = [
            {**item, "screen": text_overlap_features(record, item["record"])}
            for item in raw
        ]
        cascade = sorted(
            enriched,
            key=lambda item: item["screen"]["containment"],
            reverse=True,
        )
        raw_candidates[record["record_id"]] = raw
        capped_candidates[record["record_id"]] = capped
        tight_candidates[record["record_id"]] = tight[:25]
        cascade_candidates[record["record_id"]] = cascade[:25]
        histogram[_bucket(len(raw))] += 1
        if index % 250 == 0:
            print(json.dumps({"candidate_progress": index}), file=sys.stderr, flush=True)

    import csv
    with open(args.ground_truth, newline="", encoding="utf-8-sig") as handle:
        gt_rows = list(csv.DictReader(handle))
    gt_current_retrieved = 0
    gt_current_top = 0
    gt_tight_retrieved = 0
    gt_tight_top = 0
    gt_cascade_top = 0
    gt_true_screen_scores = []
    for row in gt_rows:
        new_id = row["superseding_record_id"]
        prior_id = row["superseded_record_id"]
        current_ids = [item["record"]["record_id"] for item in capped_candidates.get(new_id, [])]
        tight_ids = [item["record"]["record_id"] for item in tight_candidates.get(new_id, [])]
        cascade = cascade_candidates.get(new_id, [])
        cascade_ids = [item["record"]["record_id"] for item in cascade]
        gt_current_retrieved += prior_id in current_ids
        gt_current_top += bool(current_ids and current_ids[0] == prior_id)
        gt_tight_retrieved += prior_id in tight_ids
        gt_tight_top += bool(tight_ids and tight_ids[0] == prior_id)
        gt_cascade_top += bool(cascade_ids and cascade_ids[0] == prior_id)
        true_item = next(item for item in cascade if item["record"]["record_id"] == prior_id)
        gt_true_screen_scores.append(true_item["screen"]["screen_score"])

    threshold = min(gt_true_screen_scores)
    cascade_model_records = sum(
        bool(items) and items[0]["screen"]["screen_score"] >= threshold
        for items in cascade_candidates.values()
    )

    # Replay the exact chronological 103-record partial run using cache only.
    adapter = get_adapter("maintenance")
    replay = GraphRepository(MemoryGraphStore())
    MaintenanceAgent(replay, None).run({"csv_path": args.corpus})
    outputs = []
    for record in records[: args.partial]:
        outputs.append(process_record(
            replay, CacheOnlyGroq(), adapter, record["record_id"], allow_stub=False
        ))
    replay_records = {row["record_id"]: row for row in replay.list_service_records()}
    analysed = [replay_records[row["record_id"]] for row in records[: args.partial]]
    label_counts = Counter(row.get("classification_label") or "none" for row in analysed)
    score_counts = Counter(str(row.get("confidence")) for row in analysed)
    corrections = replay.list_corrections_page(limit=100, offset=0)["items"]
    random.Random(20261017).shuffle(corrections)
    samples = []
    for item in corrections[:10]:
        newer = by_id[item["newer_record"]["id"]]
        older = by_id[item["older_record"]["id"]]
        samples.append({
            "newer": {key: newer.get(key) for key in ("record_id", "occurred_at", "part_name", "jasc_code", "text")},
            "older": {key: older.get(key) for key in ("record_id", "occurred_at", "part_name", "jasc_code", "text")},
            "confidence": item.get("score"),
            "rationale": item.get("rationale"),
        })

    cache_path = Path(__file__).resolve().parent.parent / "data" / "cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    tight_model_records = sum(bool(items) for items in tight_candidates.values())
    result = {
        "ingest": ingest,
        "candidate_rule": {
            "histogram_uncapped": dict(sorted(histogram.items())),
            "records_with_candidates": sum(bool(items) for items in raw_candidates.values()),
            "raw_positive_score_pairs": sum(len(items) for items in raw_candidates.values()),
            "pairs_after_25_cap": sum(len(items) for items in capped_candidates.values()),
            "pairs_sent_per_model_record": 1,
            "self_consistency_requests_per_sent_pair": 5,
        },
        "option_a_tight_gate": {
            "records_with_candidates": tight_model_records,
            "projected_requests_at_5_passes": tight_model_records * 5,
            "ground_truth_n": len(gt_rows),
            "current_retrieved": gt_current_retrieved,
            "current_top1": gt_current_top,
            "tight_retrieved": gt_tight_retrieved,
            "tight_top1": gt_tight_top,
        },
        "cascade_screen": {
            "dev_threshold_max_retaining_all": threshold,
            "ground_truth_retained": sum(score >= threshold for score in gt_true_screen_scores),
            "ground_truth_n": len(gt_true_screen_scores),
            "old_top1": gt_current_top,
            "containment_first_top1": gt_cascade_top,
            "eligible_before_screen": sum(bool(items) for items in cascade_candidates.values()),
            "eligible_after_screen": cascade_model_records,
            "screened_free": sum(bool(items) for items in cascade_candidates.values()) - cascade_model_records,
        },
        "cache": {
            "entries": len(cache),
            "schema_has_votes": any("votes" in value for value in cache.values()),
            "schema_has_usage": any("usage" in value for value in cache.values()),
        },
        "partial_replay": {
            "records": len(analysed),
            "label_counts": dict(sorted(label_counts.items())),
            "score_histogram": dict(sorted(score_counts.items())),
            "distinct_scores": len(score_counts),
            "largest_score_bin": max(score_counts.values()),
            "largest_score_bin_share": max(score_counts.values()) / len(analysed),
            "analysis_status": replay.analysis_status(),
            "supersedes": len(corrections),
            "vote_agreement": "UNAVAILABLE: cache stores only the majority result",
            "random_supersedes_seed": 20261017,
            "random_supersedes": samples,
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
