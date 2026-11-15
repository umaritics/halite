"""Benchmark local/openai-compatible LLM on held-out ground-truth pairs (Neo4j records)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re

from config import settings
from main import lifespan
from fastapi import FastAPI
from services.conflict_engine import classify_conflict, _VALID_LABELS

_SUPP_ID = re.compile(
    r"SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*([A-Z0-9]{6,})\s*\)?",
    re.IGNORECASE,
)

_POSITIVE_LABELS = frozenset({"supersedes", "partial_supersedes", "contradicts"})


def _load_pairs_from_graph(graph_repo, limit: int) -> list[dict]:
    """FAA-style positives: new record text cites prior OperatorControlNumber."""
    if graph_repo.is_memory:
        rows = [
            r for r in graph_repo.store.service_records.values()
            if "SUPPLEMENTAL REPORT FOR" in (r.get("text") or "").upper()
        ]
    else:
        rows = graph_repo.store.run_query(
            """
            MATCH (sr:ServiceRecord)
            WHERE toUpper(sr.text) CONTAINS 'SUPPLEMENTAL REPORT FOR'
            RETURN sr AS sr
            ORDER BY sr.occurred_at
            LIMIT $limit
            """,
            {"limit": limit * 3},
        )
        rows = [item["sr"] for item in rows]
    pairs: list[dict] = []
    for rec in rows:
        text = rec.get("text") or ""
        match = _SUPP_ID.search(text)
        if not match:
            continue
        prior_id = match.group(1)
        new_id = rec.get("record_id") or rec.get("id")
        if not new_id or new_id == prior_id:
            continue
        pairs.append({"superseding_record_id": new_id, "superseded_record_id": prior_id})
        if len(pairs) >= limit:
            break
    return pairs


def _load_pairs(path: Path, limit: int | None) -> list[dict]:
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ground-truth",
        default=str(Path(settings.MAINT_DATA_DIR) / "processed" / "ground_truth_pairs.csv"),
    )
    parser.add_argument("--limit", type=int, default=25, help="Pairs to classify (default 25)")
    parser.add_argument("--passes", type=int, default=1, help="Votes per pair (1 = fast smoke)")
    parser.add_argument(
        "--from-graph-supplemental",
        action="store_true",
        help="Derive FAA citation pairs from Neo4j (no ground_truth_pairs.csv)",
    )
    args = parser.parse_args()

    app = FastAPI(lifespan=lifespan)
    import asyncio

    async def _boot():
        async with lifespan(app):
            return app.state.graph_repo, app.state.groq_service

    graph_repo, groq_service = asyncio.run(_boot())
    if not groq_service.is_live:
        raise SystemExit("LLM is not live (check LLM_PROVIDER / keys)")

    if args.from_graph_supplemental:
        pairs = _load_pairs_from_graph(graph_repo, args.limit)
    else:
        gt_path = Path(args.ground_truth)
        if not gt_path.is_file():
            raise SystemExit(f"Ground truth file not found: {gt_path}")
        pairs = _load_pairs(gt_path, args.limit)
    results: list[dict] = []
    label_hist: Counter[str] = Counter()
    parse_fail = 0

    import os

    prev_passes = os.environ.get("MAINT_SELF_CONSISTENCY_PASSES")
    os.environ["MAINT_SELF_CONSISTENCY_PASSES"] = str(max(1, args.passes))

    try:
        for row in pairs:
            new_id = row["superseding_record_id"]
            prior_id = row["superseded_record_id"]
            new_rec = graph_repo.get_service_record(new_id)
            prior_rec = graph_repo.get_service_record(prior_id)
            if not new_rec or not prior_rec:
                results.append(
                    {"new_id": new_id, "prior_id": prior_id, "error": "record_missing_in_graph"}
                )
                continue
            try:
                clf = classify_conflict(
                    groq_service,
                    new_rec,
                    prior_rec,
                    analysis_mode=settings.MAINT_ANALYSIS_MODE,
                )
            except Exception as exc:
                results.append(
                    {"new_id": new_id, "prior_id": prior_id, "error": str(exc)}
                )
                continue
            label = clf.get("label", "no_conflict")
            if clf.get("parse_failed"):
                parse_fail += 1
                label = "parse_failed"
            label_hist[label] += 1
            positive = label in _POSITIVE_LABELS
            results.append(
                {
                    "new_id": new_id,
                    "prior_id": prior_id,
                    "label": label,
                    "positive_conflict_signal": positive,
                    "vote_agreement": clf.get("vote_agreement"),
                    "parse_failed": bool(clf.get("parse_failed")),
                }
            )
    finally:
        if prev_passes is None:
            os.environ.pop("MAINT_SELF_CONSISTENCY_PASSES", None)
        else:
            os.environ["MAINT_SELF_CONSISTENCY_PASSES"] = prev_passes

    scored = [r for r in results if "label" in r]
    positive_rate = sum(1 for r in scored if r["positive_conflict_signal"]) / len(scored) if scored else 0.0
    summary = {
        "model": settings.llm_model,
        "llm_provider": settings.LLM_PROVIDER,
        "analysis_mode": settings.MAINT_ANALYSIS_MODE,
        "pairs_requested": len(pairs),
        "pairs_scored": len(scored),
        "missing_in_graph": sum(1 for r in results if r.get("error") == "record_missing_in_graph"),
        "errors": sum(1 for r in results if r.get("error") and r.get("error") != "record_missing_in_graph"),
        "parse_failures": parse_fail,
        "positive_label_rate": round(positive_rate, 4),
        "label_histogram": dict(label_hist),
        "valid_labels": sorted(_VALID_LABELS),
        "results": results,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()