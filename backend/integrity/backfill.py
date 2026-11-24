"""Store proposed_prior_id on records analysed before the field existed.

Run from backend/:  python -m integrity.backfill --dry-run
The prior is found deterministically (integrity.proposal.resolve_prior); no model is called.
A record a person has decided is left alone.
"""
from __future__ import annotations

import argparse

from . import apply
from .proposal import resolve_prior

ANALYSED_STATES = ("scored", "needs_review", "reviewed")
PAGE_SIZE = 100


def _analysed_records(graph_repo):
    """Every analysed record, one page at a time in a stable order."""
    for state in ANALYSED_STATES:
        offset = 0
        while offset is not None:
            page = graph_repo.list_service_records_page(
                analysis_state=state, sort="record_id_asc", limit=PAGE_SIZE, offset=offset,
            )
            yield from page["items"]
            offset = page["next"]


def backfill_proposed_priors(graph_repo, *, dry_run: bool) -> dict:
    """Set proposed_prior_id where it is missing; return the counts, writing nothing when dry_run."""
    counts = {"examined": 0, "would_set": 0, "no_prior_found": 0, "skipped_reviewed": 0}
    for record in _analysed_records(graph_repo):
        if record.get("proposed_prior_id") is not None:
            continue
        counts["examined"] += 1
        if apply.is_human_decided(record):
            counts["skipped_reviewed"] += 1
            continue
        prior_id, source = resolve_prior(graph_repo, record)
        if source != "recomputed":
            counts["no_prior_found"] += 1
            continue
        counts["would_set"] += 1
        if not dry_run:
            graph_repo.update_service_record(record["record_id"], {"proposed_prior_id": prior_id})
    return counts


def main() -> None:
    from config import settings
    from graph.neo4j_client import Neo4jClient
    from graph.queries import GraphRepository

    parser = argparse.ArgumentParser(description="Backfill proposed_prior_id without calling a model")
    parser.add_argument("--dry-run", action="store_true", help="print the counts and write nothing")
    args = parser.parse_args()

    repo = GraphRepository(Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))
    counts = backfill_proposed_priors(repo, dry_run=args.dry_run)
    print(("dry run: " if args.dry_run else "") + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
