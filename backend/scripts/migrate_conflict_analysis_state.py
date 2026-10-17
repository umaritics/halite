"""Migrate untouched confidence=1.0 ingest placeholders to honest unscored state.

Dry-run is the default. Use ``--apply`` to mutate, or ``--restore`` to restore
only records previously changed by this migration and not subsequently scored.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository

ANALYSIS_METADATA = (
    "analysis_state", "scored_at", "classification_label",
    "classification_rationale", "candidate_count", "candidates_considered",
    "analysis_model",
)


def is_legacy_placeholder(record: dict) -> bool:
    return (
        record.get("confidence") == 1.0
        and record.get("legacy_confidence") is None
        and not any(record.get(key) is not None for key in ANALYSIS_METADATA)
    )


def is_restorable(record: dict) -> bool:
    return (
        record.get("legacy_confidence") is not None
        and record.get("analysis_state") == "unscored"
        and record.get("confidence") is None
        and record.get("scored_at") is None
    )


def summarize(records: list[dict]) -> dict:
    return {
        "total": len(records),
        "legacy_placeholders": sum(is_legacy_placeholder(r) for r in records),
        "unscored": sum((r.get("analysis_state") or "unscored") == "unscored" for r in records),
        "scored_or_reviewed": sum((r.get("analysis_state") or "unscored") != "unscored" for r in records),
        "with_legacy_confidence": sum(r.get("legacy_confidence") is not None for r in records),
    }


def migrate(repo, *, apply: bool = False, restore: bool = False) -> dict:
    records = repo.list_service_records()
    before = summarize(records)
    candidates = (
        [r for r in records if is_restorable(r)]
        if restore
        else [r for r in records if is_legacy_placeholder(r)]
    )
    if apply or restore:
        for record in candidates:
            if restore:
                repo.update_service_record(record["record_id"], {
                    "confidence": record["legacy_confidence"],
                    "status": record.get("legacy_status") or "auto_accepted",
                    "analysis_state": None,
                    "legacy_confidence": None,
                    "legacy_status": None,
                })
            else:
                repo.update_service_record(record["record_id"], {
                    "legacy_confidence": record["confidence"],
                    "legacy_status": record.get("status"),
                    "confidence": None,
                    "status": "unscored",
                    "analysis_state": "unscored",
                })
    after = summarize(repo.list_service_records()) if apply or restore else before
    return {
        "mode": "restore" if restore else ("apply" if apply else "dry_run"),
        "would_change" if not (apply or restore) else "changed": len(candidates),
        "before": before,
        "after": after,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Apply the migration")
    group.add_argument("--restore", action="store_true", help="Restore untouched migrated placeholders")
    args = parser.parse_args()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    try:
        result = migrate(GraphRepository(client), apply=args.apply, restore=args.restore)
        print(json.dumps(result, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
