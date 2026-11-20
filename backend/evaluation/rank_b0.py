"""
Frozen B0 mid-term ranker (pre B1 fixes) — benchmark only, not served in production.

Differences from B1 (services/diagnostic_retrieval.py):
- Fleet exclude compares exclude_asset_id only to asset_key (UUID leak).
- Asset history uses recency only (no symptom overlap).
- Superseded flag: status string only.
"""
from __future__ import annotations

import re
from typing import Optional

from services.diagnostic_retrieval import (
    FLEET_SCAN_CAP,
    RANK_SUPERSEDED_PENALTY,
    RANK_WEIGHT_ASSET_HISTORY,
    RANK_WEIGHT_FLEET_MATCH,
    asset_history_context,
    resolution_outcomes,
    _normalise,
    _text_similarity,
)


def _record_is_superseded_b0(record: dict) -> bool:
    return record.get("status") == "superseded"


def similar_symptom_records_b0(
    graph_repo,
    symptom_text: str,
    jasc_code: Optional[str] = None,
    exclude_asset_id: Optional[str] = None,
    limit: int = 20,
    exclude_synthetic: bool = True,
) -> list[dict]:
    all_records = graph_repo.list_service_records(limit=FLEET_SCAN_CAP)
    scored = []
    norm_jasc = _normalise(jasc_code) if jasc_code else ""

    for rec in all_records:
        rec_asset = rec.get("asset_key") or rec.get("asset_id") or ""
        rec_id = str(rec.get("record_id", rec.get("id", "")))
        if exclude_synthetic and rec_id.startswith("DEMO"):
            continue
        if exclude_asset_id and (
            rec_asset == exclude_asset_id or rec.get("id") == exclude_asset_id
        ):
            continue

        score = 0.0
        if norm_jasc and _normalise(rec.get("jasc_code", "")) == norm_jasc:
            score += 0.50
        part_sim = _text_similarity(symptom_text, rec.get("part_name", ""))
        score += part_sim * 0.30
        text_sim = _text_similarity(symptom_text, rec.get("text", ""))
        score += text_sim * 0.20
        if score < 0.05:
            continue
        is_sup = _record_is_superseded_b0(rec)
        scored.append(
            {
                "record_id": rec.get("record_id", rec.get("id", "")),
                "asset_id": rec_asset,
                "occurred_at": rec.get("occurred_at", ""),
                "part_name": rec.get("part_name", ""),
                "jasc_code": rec.get("jasc_code", ""),
                "text": rec.get("text", ""),
                "status": rec.get("status", ""),
                "is_superseded": is_sup,
                "score": round(score, 4),
            }
        )
    scored.sort(key=lambda x: (-x["score"], str(x["record_id"])))
    return scored[:limit]


def build_diagnostic_context_b0(graph_repo, asset_id: str, symptom_text: str) -> dict:
    history = asset_history_context(graph_repo, asset_id, limit=30)
    jasc_hint = None
    for h in history:
        if _text_similarity(symptom_text, h.get("part_name", "")) > 0.2:
            jasc_hint = h.get("jasc_code") or None
            break
    fleet = similar_symptom_records_b0(
        graph_repo,
        symptom_text,
        jasc_code=jasc_hint,
        exclude_asset_id=asset_id,
        limit=20,
    )
    all_ids = [r["record_id"] for r in history] + [r["record_id"] for r in fleet]
    outcomes = resolution_outcomes(graph_repo, all_ids)
    return {
        "asset_id": asset_id,
        "symptom_text": symptom_text,
        "asset_history": history,
        "fleet_matches": fleet,
        "resolution_outcomes": outcomes,
        "context_size": {
            "asset_records": len(history),
            "fleet_records": len(fleet),
            "fleet_assets": len({r["asset_id"] for r in fleet if r["asset_id"]}),
        },
    }


def rank_diagnostic_checks_b0(context: dict) -> list[dict]:
    component_scores: dict[str, dict] = {}

    def _add(part: str, weight: float, source: str, record_id: str) -> None:
        if not part or part.upper().strip() in ("UNKNOWN", ""):
            return
        key = part.upper().strip()
        if key not in component_scores:
            component_scores[key] = {
                "part_name": key,
                "score": 0.0,
                "evidence_count": 0,
                "evidence_record_ids": [],
                "sources": [],
            }
        bucket = component_scores[key]
        bucket["score"] += weight
        if record_id and record_id not in bucket["evidence_record_ids"]:
            bucket["evidence_count"] += 1
            bucket["evidence_record_ids"].append(record_id)
        if source not in bucket["sources"]:
            bucket["sources"].append(source)

    for i, rec in enumerate(context.get("asset_history") or []):
        recency_weight = 1.0 / (i + 1)
        superseded_penalty = (
            RANK_SUPERSEDED_PENALTY if rec.get("is_superseded") else 1.0
        )
        _add(
            rec.get("part_name", ""),
            recency_weight * superseded_penalty * RANK_WEIGHT_ASSET_HISTORY,
            "asset_history",
            rec.get("record_id", ""),
        )

    for rec in context.get("fleet_matches") or []:
        fleet_score = float(rec.get("score") or 0.1)
        superseded_penalty = (
            RANK_SUPERSEDED_PENALTY if rec.get("is_superseded") else 1.0
        )
        _add(
            rec.get("part_name", ""),
            fleet_score * superseded_penalty * RANK_WEIGHT_FLEET_MATCH,
            "fleet_match",
            rec.get("record_id", ""),
        )

    ranked = sorted(
        component_scores.values(),
        key=lambda x: (-x["score"], -x["evidence_count"], x["part_name"]),
    )
    for i, item in enumerate(ranked):
        item["rank"] = i + 1
        item["score"] = round(item["score"], 4)
        item["evidence_record_ids"] = sorted(item["evidence_record_ids"])
        item["sources"] = sorted(item["sources"])
    return ranked