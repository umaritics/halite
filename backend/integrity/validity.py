"""Whether a report is still current, read from SUPERSEDES links and never from the status string.

The status string is overwritten when a record is re-processed; the link is the record of the decision.
"""
from __future__ import annotations

from .timeutil import parse_submitted

_METHOD_RANK = {"human": 0, "explicit_citation": 1, "model": 2}


def _preference(link: dict):
    """Sort key: the most trusted decision first, then the latest, then the smallest ID."""
    decided = parse_submitted(link.get("decided_at")) or parse_submitted(link.get("created_at"))
    return (
        _METHOD_RANK.get(link.get("method") or "model", len(_METHOD_RANK)),
        -(decided.timestamp() if decided else 0.0),
        link["new_record_id"],
    )


def superseded_by(graph_repo, record_ids: list[str]) -> dict[str, str]:
    """Map each superseded record_id to the record_id that supersedes it.

    When several links supersede one record, a human decision beats an explicit citation,
    which beats a model guess; ties go to the latest decision, then the smallest ID, so the answer is stable.
    """
    best: dict[str, dict] = {}
    for link in graph_repo.list_supersedes_links(record_ids):
        old_id = link["old_record_id"]
        if old_id not in best or _preference(link) < _preference(best[old_id]):
            best[old_id] = link
    return {old_id: link["new_record_id"] for old_id, link in best.items()}


def is_current(record: dict, superseded: dict[str, str]) -> bool:
    """True when no link supersedes this record."""
    return record.get("record_id") not in superseded
