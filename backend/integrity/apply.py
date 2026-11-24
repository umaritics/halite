"""The single writer: every SUPERSEDES / NOT_SUPERSEDES link and every integrity status change goes through here.

One door means one place to enforce that a human decision is never overwritten by code, and one
place to emit the audit trail. The caller supplies `audit(action, record_id, metadata)`; this module
never imports the database.
"""
from __future__ import annotations

from .citations import parse_citations
from .timeutil import is_eligible_prior

HUMAN_STATUSES = ("accepted", "rejected")


def _emit(audit, action: str, record_id: str, metadata: dict) -> None:
    if audit is not None:
        audit(action, record_id, metadata)


def is_human_decided(record: dict | None) -> bool:
    """True once a reviewer has decided the record; code must then leave it alone."""
    if not record:
        return False
    return record.get("analysis_state") == "reviewed" or record.get("status") in HUMAN_STATUSES


def link_supersedes(
    graph_repo, new_id: str, old_id: str, *, scope: str, confidence: float, rationale: str,
    method: str, model_version: str = "", decided_by: str = "", decided_at: str = "", audit=None,
) -> bool:
    """Write new -> old SUPERSEDES and mark the old record superseded; False when a human rejected the pair.

    The prior status is remembered so that removing the link can restore it. A human-decided
    old record keeps its status: the link records the supersession, the reviewer's word stays.
    """
    if method != "human" and old_id in graph_repo.rejected_prior_ids(new_id):
        return False
    existed = graph_repo.get_supersedes_link(new_id, old_id) is not None
    graph_repo.link_record_supersedes(
        new_id, old_id, scope, confidence, rationale, method=method, model_version=model_version,
        decided_by=decided_by, decided_at=decided_at,
    )
    old = graph_repo.get_service_record(old_id)
    if old is not None and not is_human_decided(old):
        updates = {"status": "superseded"}
        if old.get("status") != "superseded":
            updates["status_before_superseded"] = old.get("status") or "unscored"
        graph_repo.update_service_record(old_id, updates)
    if not existed:
        _emit(audit, "integrity.link.created", new_id, {"prior_record_id": old_id, "method": method})
    return True


def unlink_supersedes(graph_repo, new_id: str, old_id: str, *, audit=None) -> bool:
    """Delete the link; the old record gets its previous status back unless another link still supersedes it."""
    if not graph_repo.unlink_record_supersedes(new_id, old_id):
        return False
    old = graph_repo.get_service_record(old_id)
    still_superseded = bool(graph_repo.list_supersedes_links([old_id]))
    if old is not None and old.get("status") == "superseded" and not still_superseded:
        graph_repo.update_service_record(
            old_id, {"status": old.get("status_before_superseded") or "unscored"}
        )
    _emit(audit, "integrity.link.removed", new_id, {"prior_record_id": old_id})
    return True


def apply_explicit_citations(graph_repo, record: dict, *, dry_run: bool = False, audit=None) -> dict:
    """Rule R1: link a report to the earlier same-aircraft reports it names; no model is asked.

    Returns cited_record_ids, linked, missing and ineligible (each with its reason), so the
    engine can tell "the prior is not in our corpus" apart from "the citation does not hold".
    """
    new_id = record["record_id"]
    cited = parse_citations(record.get("text"))
    result: dict = {"cited_record_ids": cited, "linked": [], "missing": [], "ineligible": []}
    rejected = graph_repo.rejected_prior_ids(new_id)
    for cited_id in cited:
        prior = graph_repo.get_service_record(cited_id)
        if prior is None:
            result["missing"].append(cited_id)
            continue
        reason = "a reviewer rejected this pair" if cited_id in rejected else _citation_problem(record, prior)
        if reason is None and not dry_run:
            link_supersedes(
                graph_repo, new_id, cited_id, scope="supersedes", confidence=1.0,
                rationale=f"The report cites {cited_id} as the report it supplements.",
                method="explicit_citation", audit=audit,
            )
        if reason is None:
            result["linked"].append(cited_id)
        else:
            result["ineligible"].append({"record_id": cited_id, "reason": reason})
    if cited and not dry_run:
        graph_repo.update_service_record(new_id, {"cited_record_ids": cited})
    return result


def _citation_problem(record: dict, prior: dict) -> str | None:
    """Why a cited report cannot be superseded by `record`, or None when it can."""
    if prior.get("record_id") == record.get("record_id"):
        return "a report cannot supersede itself"
    asset_key = record.get("asset_key")
    if not asset_key or asset_key != prior.get("asset_key"):
        return "the cited report is on a different aircraft"
    if not is_eligible_prior(record, prior):
        return "the cited report was not submitted before this one"
    return None


def record_analysis(graph_repo, record_id: str, updates: dict, *, force: bool = False, audit=None) -> dict | None:
    """Write the target record's status and analysis fields; None when a human decided it and force is off."""
    record = graph_repo.get_service_record(record_id)
    if record is None:
        return None
    if is_human_decided(record) and not force:
        return None
    before = record.get("status")
    written = graph_repo.update_service_record(record_id, updates)
    after = updates.get("status", before)
    if after != before:
        _emit(audit, "integrity.status.changed", record_id, {
            "from": before, "to": after, "method": updates.get("analysis_method", ""),
        })
    return written
