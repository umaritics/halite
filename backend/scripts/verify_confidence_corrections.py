"""Run confidence/corrections verification on the real CSV in an in-memory graph.

This never connects to Neo4j. ``--simulate-legacy`` changes only the ephemeral
copy so the migration can be demonstrated against the deployed placeholder
shape before the same real records are analysed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.maintenance_agent import MaintenanceAgent
from config import settings
from domains.registry import get_adapter
from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from scripts.migrate_conflict_analysis_state import migrate
from services.conflict_engine import process_record
from services.groq_service import GroqService


class CountingGroq:
    def __init__(self, inner):
        self.inner = inner
        self.model = inner.model
        self.requests = 0

    @property
    def is_live(self):
        return self.inner.is_live

    def extract_json(self, *args, **kwargs):
        self.requests += 1
        return self.inner.extract_json(*args, **kwargs)


def _score_range(record: dict) -> str:
    score = record.get("confidence")
    if score is None:
        return "null"
    if score == 0:
        return "0"
    if score < 0.5:
        return "(0,0.5)"
    if score < 0.75:
        return "[0.5,0.75)"
    return "[0.75,1.0]"


def _snapshot(repo, started_at: float, model_records: int, groq: CountingGroq) -> dict:
    records = repo.list_service_records()
    distribution = Counter(
        (
            record.get("analysis_state") or "unscored",
            record.get("classification_label") or "none",
            _score_range(record),
        )
        for record in records
    )
    corrections = repo.list_corrections_page(limit=100, offset=0)
    return {
        "elapsed_seconds": round(time.perf_counter() - started_at, 2),
        "analysis_status": repo.analysis_status(),
        "model_records": model_records,
        "live_llm_requests": groq.requests,
        "review_queue_size": len(repo.list_service_records(status="needs_review")),
        "supersedes_edges": sum(1 for edge in repo.store.edges if edge["type"] == "SUPERSEDES"),
        "corrections_summary": corrections["summary"],
        "distribution": [
            {"analysis_state": state, "label": label, "score_range": score_range, "count": count}
            for (state, label, score_range), count in sorted(distribution.items())
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--simulate-legacy", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args()

    started_at = time.perf_counter()
    repo = GraphRepository(MemoryGraphStore())
    ingest = MaintenanceAgent(repo, None).run({"csv_path": args.corpus})
    records = repo.list_service_records()
    records.sort(key=lambda record: (record.get("occurred_at", ""), record.get("record_id", "")))
    if args.limit:
        records = records[:args.limit]

    if args.simulate_legacy:
        for record in records:
            repo.update_service_record(record["record_id"], {
                "status": "auto_accepted", "analysis_state": None, "confidence": 1.0,
            })

    migration_dry_run = migrate(repo)
    migration_apply = migrate(repo, apply=True)
    groq = CountingGroq(GroqService(settings.GROQ_API_KEY, settings.GROQ_MODEL))
    if not groq.is_live:
        raise SystemExit("Live Groq is required; refusing fallback output.")

    adapter = get_adapter("maintenance")
    model_records = 0
    processed = 0
    try:
        for record in records:
            if (repo.get_service_record(record["record_id"]).get("analysis_state") or "unscored") != "unscored":
                continue
            last_error = None
            for attempt in range(3):
                try:
                    result = process_record(
                        repo, groq, adapter, record["record_id"],
                        threshold=settings.MAINT_CONFIDENCE_THRESHOLD,
                        allow_stub=False,
                    )
                    last_error = None
                    break
                except RuntimeError as exc:
                    last_error = exc
                    if "429" not in str(exc) and "rate limit" not in str(exc).lower():
                        raise
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
            if last_error:
                raise last_error
            processed += 1
            model_records += int(result["candidates_considered"] > 0)
            if processed % args.progress_every == 0:
                print(json.dumps({
                    "progress": processed,
                    "total": len(records),
                    "model_records": model_records,
                    "live_llm_requests": groq.requests,
                    "remaining_unscored": repo.analysis_status()["unscored"],
                }), flush=True)
    except Exception as exc:
        print(json.dumps({
            "completed": False,
            "error": str(exc),
            "ingest": ingest,
            "migration_dry_run": migration_dry_run,
            "migration_apply": migration_apply,
            "processed": processed,
            "partial": _snapshot(repo, started_at, model_records, groq),
        }, indent=2), flush=True)
        raise

    print(json.dumps({
        "completed": True,
        "model": settings.GROQ_MODEL,
        "self_consistency_passes": int(os.environ.get("MAINT_SELF_CONSISTENCY_PASSES", "5")),
        "threshold": settings.MAINT_CONFIDENCE_THRESHOLD,
        "ingest": ingest,
        "migration_dry_run": migration_dry_run,
        "migration_apply": migration_apply,
        "processed": processed,
        "result": _snapshot(repo, started_at, model_records, groq),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
