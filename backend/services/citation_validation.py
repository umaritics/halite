"""
Citation extraction and graph verification for diagnostic LLM output.

Only record IDs that exist in the graph are treated as valid citations.
Invented or mistyped IDs are flagged — never silently accepted.
"""
from __future__ import annotations

import re

# Real FAA SDR shapes observed in Mid-I corpus, e.g. SWIA2025091876593, AALA202504075792.
# Also accepts shorter alphanumeric demo IDs used in MemoryGraphStore tests (R1_OLD excluded —
# underscore IDs are not matched; tests seed SWIA… / AALA… style when needed).
_RECORD_ID_RE = re.compile(r"\b([A-Z]{2,6}\d{6,})\b")


def extract_record_id_candidates(text: str) -> list[str]:
    """Return unique FAA-shaped ID tokens in appearance order."""
    if not text:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _RECORD_ID_RE.findall(text):
        if match not in seen:
            seen.add(match)
            ordered.append(match)
    return ordered


def validate_citations(text: str, graph_repo) -> dict:
    """
    Verify every extracted ID against the graph.

    Returns:
      valid: list[str]
      invalid: list[str]
      flagged_text: str  — invalid IDs wrapped as [UNVERIFIED:ID]
    """
    found = extract_record_id_candidates(text)
    if not found:
        return {"valid": [], "invalid": [], "flagged_text": text or ""}

    by_id: dict[str, dict] = {}
    if hasattr(graph_repo, "get_service_records_by_ids"):
        for rec in graph_repo.get_service_records_by_ids(found):
            rid = str(rec.get("record_id", rec.get("id", "")))
            if rid:
                by_id[rid] = rec
    else:
        for rid in found:
            rec = graph_repo.get_service_record(rid)
            if rec is not None:
                by_id[str(rid)] = rec

    valid: list[str] = []
    invalid: list[str] = []
    for rid in found:
        if rid in by_id:
            valid.append(rid)
        else:
            invalid.append(rid)

    flagged = text or ""
    for rid in invalid:
        flagged = flagged.replace(rid, f"[UNVERIFIED:{rid}]")

    return {"valid": valid, "invalid": invalid, "flagged_text": flagged}
