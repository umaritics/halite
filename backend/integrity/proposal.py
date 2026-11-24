"""The proposal a reviewer is shown: read from what analysis stored, never from a model call.

Re-running the engine on every screen load could show a different pair from the one that was
scored and costs model time, so the review screen reads these stored fields instead.
"""
from __future__ import annotations

from services import conflict_engine

CHANGED_FIELDS = ("part_name", "jasc_code", "part_location", "part_condition")


def _stored_mode(record: dict) -> str:
    """The analysis mode a record was scored in, inferred because the mode itself is not stored.

    Only the cascade produces a screen result, an escalated vote or a two-vote pass, so those mark it.
    """
    cascade = record.get("analysis_method") in ("screen", "llm-escalated") or record.get("analysis_passes") == 2
    return "cascade" if cascade else "legacy"


def resolve_prior(graph_repo, record: dict) -> tuple[str, str]:
    """(prior record id, source) where source is "stored", "recomputed" or "none".

    Only a record analysed before proposed_prior_id existed (field absent) is recomputed; an
    empty value means the engine found no prior, and a later search must not invent one.
    """
    stored = record.get("proposed_prior_id")
    if stored:
        return stored, "stored"
    if stored is None:
        pairs = conflict_engine.find_candidate_pairs(
            graph_repo, record["record_id"], analysis_mode=_stored_mode(record),
        )
        if pairs:
            return pairs[0]["record"]["record_id"], "recomputed"
    return "", "none"


def pin_recomputed_prior(graph_repo, record: dict) -> dict:
    """Store a recomputed prior so a decision acts on the pair the reviewer was shown."""
    prior_id, source = resolve_prior(graph_repo, record)
    if source != "recomputed":
        return record
    return graph_repo.update_service_record(record["record_id"], {"proposed_prior_id": prior_id}) or record


def changed_fields(record: dict, prior: dict) -> list[dict]:
    """Fields where the two reports differ after trimming and case-folding."""
    changes = []
    for field in CHANGED_FIELDS:
        new_value, prior_value = (record.get(field) or "").strip(), (prior.get(field) or "").strip()
        if new_value.casefold() != prior_value.casefold():
            changes.append({"field": field, "prior": prior_value, "new": new_value})
    return changes


def stored_proposal(graph_repo, record_id: str) -> dict | None:
    """The stored proposal for a record, or None when the record does not exist."""
    record = graph_repo.get_service_record(record_id)
    if record is None:
        return None
    prior_id, source = resolve_prior(graph_repo, record)
    prior = graph_repo.get_service_record(prior_id) if prior_id else None
    return {
        "record": record,
        "proposed_prior": prior,
        "proposal_source": source if prior else "none",
        "label": record.get("classification_label"),
        "rationale": record.get("classification_rationale"),
        "confidence": record.get("confidence"),
        "method": record.get("analysis_method"),
        "model_version": record.get("integrity_model_version"),
        "cited_record_ids": record.get("cited_record_ids") or [],
        "link": graph_repo.get_supersedes_link(record_id, prior_id) if prior else None,
        "changed_fields": changed_fields(record, prior) if prior else [],
    }
