"""
backend/services/diagnostic_retrieval.py

Graph-grounded retrieval service for the maintenance diagnostic endpoint.
Every returned item carries provenance (record_id, asset, date, status).
Nothing is synthesised — every dict returned traces to a real ServiceRecord.
"""
from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().upper())


def _text_similarity(a: str, b: str) -> float:
    """Simple Jaccard similarity on word sets."""
    wa = set(_normalise(a).split())
    wb = set(_normalise(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _record_is_superseded(record: dict) -> bool:
    return record.get("status") == "superseded"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def asset_history_context(graph_repo, asset_id: str, limit: int = 30, exclude_synthetic: bool = True) -> list[dict]:
    """
    Return this asset's ServiceRecords, newest first, with status and any
    SUPERSEDES relationship indicated.

    Each item:
      record_id, asset_id, occurred_at, part_name, jasc_code, text,
      status, is_superseded, superseded_by (record_id | None)
    """
    history = graph_repo.list_asset_history(asset_id, limit=200)
    # Sort newest first
    history.sort(key=lambda r: r.get("occurred_at", ""), reverse=True)
    if exclude_synthetic:
        history = [r for r in history if not str(r.get("record_id", r.get("id", ""))).startswith("DEMO")]

    results = []
    for rec in history[:limit]:
        entry = {
            "record_id":    rec.get("record_id", rec.get("id", "")),
            "asset_id":     asset_id,
            "occurred_at":  rec.get("occurred_at", ""),
            "part_name":    rec.get("part_name", ""),
            "part_condition": rec.get("part_condition", ""),
            "part_location":  rec.get("part_location", ""),
            "jasc_code":    rec.get("jasc_code", ""),
            "text":         rec.get("text", ""),
            "status":       rec.get("status", ""),
            "is_superseded":   _record_is_superseded(rec),
            "superseded_by":   rec.get("superseding_record"),   # filled by graph if stored
            "confidence":   rec.get("confidence"),
        }
        results.append(entry)

    return results


def similar_symptom_records(
    graph_repo,
    symptom_text: str,
    jasc_code: Optional[str] = None,
    exclude_asset_id: Optional[str] = None,
    limit: int = 20,
    exclude_synthetic: bool = True,
) -> list[dict]:
    """
    Fleet-wide retrieval: records on *other* assets matching the symptom.

    Scoring (0-1 additive):
      +0.50  JASCCode exact match
      +0.30  PartName overlap (Jaccard word)
      +0.20  text similarity (Jaccard word)

    Only non-superseded records score positively; superseded ones are included
    if they score ≥ 0.2 but are flagged as is_superseded=True.

    Returns list sorted descending by score.
    """
    # Collect all records across all assets
    all_records = graph_repo.list_service_records()

    scored = []
    norm_jasc = _normalise(jasc_code) if jasc_code else ""

    for rec in all_records:
        rec_asset = rec.get("asset_key") or rec.get("asset_id") or ""
        rec_id = str(rec.get("record_id", rec.get("id", "")))

        if exclude_synthetic and rec_id.startswith("DEMO"):
            continue

        # Skip own asset
        if exclude_asset_id and (rec_asset == exclude_asset_id or
                                  rec.get("id") == exclude_asset_id):
            continue

        score = 0.0

        # JASC match
        if norm_jasc and _normalise(rec.get("jasc_code", "")) == norm_jasc:
            score += 0.50

        # Part name overlap
        part_sim = _text_similarity(symptom_text, rec.get("part_name", ""))
        score += part_sim * 0.30

        # Text similarity
        text_sim = _text_similarity(symptom_text, rec.get("text", ""))
        score += text_sim * 0.20

        if score < 0.05:
            continue

        is_sup = _record_is_superseded(rec)
        scored.append({
            "record_id":     rec.get("record_id", rec.get("id", "")),
            "asset_id":      rec_asset,
            "occurred_at":   rec.get("occurred_at", ""),
            "part_name":     rec.get("part_name", ""),
            "jasc_code":     rec.get("jasc_code", ""),
            "text":          rec.get("text", ""),
            "status":        rec.get("status", ""),
            "is_superseded": is_sup,
            "score":         round(score, 4),
            "confidence":    rec.get("confidence"),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def resolution_outcomes(graph_repo, record_ids: list[str]) -> list[dict]:
    """
    For each record_id return its outcome: the record text (corrective action),
    whether the record itself was later superseded (=negative signal), and
    the superseding record if known.

    Superseded resolutions are labelled explicitly — they must not be silently
    presented as positive evidence.
    """
    results = []
    for rid in record_ids:
        rec = graph_repo.get_service_record(rid)
        if rec is None:
            continue
        is_sup = _record_is_superseded(rec)
        results.append({
            "record_id":        rid,
            "status":           rec.get("status", ""),
            "is_superseded":    is_sup,
            "superseded_by":    rec.get("superseding_record"),
            "resolution_text":  rec.get("text", ""),
            "part_name":        rec.get("part_name", ""),
            "occurred_at":      rec.get("occurred_at", ""),
            "confidence":       rec.get("confidence"),
        })
    return results


def build_diagnostic_context(
    graph_repo,
    asset_id: str,
    symptom_text: str,
    exclude_synthetic: bool = True,
) -> dict:
    """
    Assemble the full diagnostic payload for (asset_id, symptom_text).

    Returns:
      {
        "asset_id": str,
        "symptom_text": str,
        "asset_history": list[dict],        # newest-first, limit 30
        "fleet_matches": list[dict],        # other assets, scored
        "resolution_outcomes": list[dict],  # for all retrieved record_ids
        "context_size": {
            "asset_records": int,
            "fleet_records": int,
            "fleet_assets": int,
        }
      }

    Every item in every list carries record_id, asset, date, status.
    Nothing is synthesised.
    """
    # 1. Asset's own history
    history = asset_history_context(graph_repo, asset_id, limit=30, exclude_synthetic=exclude_synthetic)

    # 2. Infer JASC from symptom by checking against asset history
    jasc_hint = None
    for h in history:
        if _text_similarity(symptom_text, h.get("part_name", "")) > 0.2:
            jasc_hint = h.get("jasc_code") or None
            break

    # 3. Fleet-wide matches (exclude own asset)
    fleet = similar_symptom_records(
        graph_repo,
        symptom_text,
        jasc_code=jasc_hint,
        exclude_asset_id=asset_id,
        limit=20,
        exclude_synthetic=exclude_synthetic,
    )

    # 4. Resolution outcomes for all retrieved records
    all_ids = [r["record_id"] for r in history] + [r["record_id"] for r in fleet]
    outcomes = resolution_outcomes(graph_repo, all_ids)

    # 5. Count distinct fleet assets
    fleet_assets = len({r["asset_id"] for r in fleet if r["asset_id"]})

    return {
        "asset_id":           asset_id,
        "symptom_text":       symptom_text,
        "asset_history":      history,
        "fleet_matches":      fleet,
        "resolution_outcomes": outcomes,
        "context_size": {
            "asset_records": len(history),
            "fleet_records": len(fleet),
            "fleet_assets":  fleet_assets,
        },
    }
