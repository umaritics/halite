"""
backend/services/diagnostic_retrieval.py

Graph-grounded retrieval service for the maintenance diagnostic endpoint.
Every returned item carries provenance (record_id, asset, date, status).
Nothing is synthesised — every dict returned traces to a real ServiceRecord.
"""
from __future__ import annotations

import re
from typing import Optional

# Mid-I FAA corpus is ~2k records. Cap fleet scan so Neo4j always has a LIMIT
# and Python scoring cannot grow unbounded if the graph grows later.
FLEET_SCAN_CAP = 2500

# Documented heuristic weights for rank_diagnostic_checks (not calibrated probs).
RANK_WEIGHT_ASSET_HISTORY = 0.4
RANK_WEIGHT_FLEET_MATCH = 0.6
RANK_SUPERSEDED_PENALTY = 0.3


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
    # Fetch newest-first with the same limit we return (bounded Cypher LIMIT).
    # Over-fetch slightly when excluding DEMO* so the visible window still fills.
    fetch_limit = limit + 20 if exclude_synthetic else limit
    history = graph_repo.list_asset_history_recent(asset_id, limit=fetch_limit)
    if exclude_synthetic:
        history = [
            r for r in history
            if not str(r.get("record_id", r.get("id", ""))).startswith("DEMO")
        ]

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
    # Bounded fleet scan (newest-first LIMIT in Neo4j / memory store).
    all_records = graph_repo.list_service_records(limit=FLEET_SCAN_CAP)

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

    # Deterministic: score DESC, then record_id ASC for equal scores.
    scored.sort(key=lambda x: (-x["score"], str(x["record_id"])))
    return scored[:limit]


def resolution_outcomes(graph_repo, record_ids: list[str]) -> list[dict]:
    """
    For each record_id return its outcome: the record text (corrective action),
    whether the record itself was later superseded (=negative signal), and
    the superseding record if known.

    Superseded resolutions are labelled explicitly — they must not be silently
    presented as positive evidence.
    """
    if not record_ids:
        return []

    by_id: dict[str, dict] = {}
    if hasattr(graph_repo, "get_service_records_by_ids"):
        for rec in graph_repo.get_service_records_by_ids(record_ids):
            rid = str(rec.get("record_id", rec.get("id", "")))
            if rid:
                by_id[rid] = rec
    else:
        for rid in record_ids:
            rec = graph_repo.get_service_record(rid)
            if rec is not None:
                by_id[str(rid)] = rec

    results = []
    for rid in record_ids:
        rec = by_id.get(str(rid))
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


def rank_diagnostic_checks(context: dict) -> list[dict]:
    """
    Deterministic inspection ranking from graph context (no LLM).

    Signals (heuristic, not calibrated probabilities):
      - Asset history: recency 1/(i+1) × RANK_WEIGHT_ASSET_HISTORY;
        superseded records × RANK_SUPERSEDED_PENALTY.
      - Fleet matches: similarity score × RANK_WEIGHT_FLEET_MATCH;
        same superseded penalty.

    Tie-break (stable across runs / Python versions):
      1. score DESC
      2. evidence_count DESC
      3. part_name ASC

    Each item: part_name, score, evidence_count, evidence_record_ids (sorted),
    sources, rank (1-based).
    """
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


# ---------------------------------------------------------------------------
# Copilot composition (additive; the frozen /diagnose path above is unchanged)
# ---------------------------------------------------------------------------

def build_copilot_context(
    graph_repo,
    asset_id: Optional[str],
    case_state: dict,
    exclude_synthetic: bool = True,
) -> dict:
    """Build bounded retrieval context from the accumulated diagnostic case.

    ``asset_id=None`` deliberately skips asset history and searches the fleet.
    Ruled-out component names are removed from the retrieval query so a later
    turn can materially change the deterministic ranking.
    """
    ruled_out = {_normalise(value) for value in case_state.get("ruled_out", []) if value}
    facts = [
        *case_state.get("symptoms", []),
        *case_state.get("observations", []),
    ]
    usable_facts = [
        str(value).strip()
        for value in facts
        if str(value).strip() and _normalise(str(value)) not in ruled_out
    ]
    query = " ".join(usable_facts).strip()

    history = (
        asset_history_context(
            graph_repo,
            asset_id,
            limit=30,
            exclude_synthetic=exclude_synthetic,
        )
        if asset_id
        else []
    )

    jasc_hint = None
    for record in history:
        if _text_similarity(query, record.get("part_name", "")) > 0.2:
            jasc_hint = record.get("jasc_code") or None
            break

    fleet = similar_symptom_records(
        graph_repo,
        query,
        jasc_code=jasc_hint,
        exclude_asset_id=asset_id,
        limit=20,
        exclude_synthetic=exclude_synthetic,
    ) if query else []

    all_ids = [record["record_id"] for record in history + fleet]
    outcomes = resolution_outcomes(graph_repo, all_ids)
    return {
        "asset_id": asset_id,
        "symptom_text": query,
        "asset_history": history,
        "fleet_matches": fleet,
        "resolution_outcomes": outcomes,
        "context_size": {
            "asset_records": len(history),
            "fleet_records": len(fleet),
            "fleet_assets": len({r["asset_id"] for r in fleet if r.get("asset_id")}),
        },
    }


def rank_copilot_checks(context: dict, ruled_out: list[str] | None = None) -> list[dict]:
    """Rank active evidence with the heuristic, excluding ruled-out parts.

    Superseded records remain in the returned context for transparency but are
    never inputs to a copilot recommendation.
    """
    excluded = {_normalise(value) for value in (ruled_out or []) if value}
    active_context = {
        **context,
        "asset_history": [r for r in context.get("asset_history", []) if not r.get("is_superseded")],
        "fleet_matches": [r for r in context.get("fleet_matches", []) if not r.get("is_superseded")],
    }
    ranked = [
        item for item in rank_diagnostic_checks(active_context)
        if _normalise(item.get("part_name", "")) not in excluded
    ]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def ranking_delta(previous: list[dict], current: list[dict]) -> dict:
    """Describe deterministic rank and evidence changes between two case states."""
    before = {item["part_name"]: item for item in previous}
    after = {item["part_name"]: item for item in current}

    moved_up = []
    moved_down = []
    new = []
    dropped = []
    for part, item in after.items():
        if part not in before:
            new.append({"part_name": part, "rank": item["rank"]})
        elif item["rank"] < before[part]["rank"]:
            moved_up.append({
                "part_name": part,
                "from_rank": before[part]["rank"],
                "to_rank": item["rank"],
            })
        elif item["rank"] > before[part]["rank"]:
            moved_down.append({
                "part_name": part,
                "from_rank": before[part]["rank"],
                "to_rank": item["rank"],
            })
    for part, item in before.items():
        if part not in after:
            dropped.append({"part_name": part, "from_rank": item["rank"]})

    before_ids = {
        record_id
        for item in previous
        for record_id in item.get("evidence_record_ids", [])
    }
    current_ids = {
        record_id
        for item in current
        for record_id in item.get("evidence_record_ids", [])
    }
    return {
        "moved_up": moved_up,
        "moved_down": moved_down,
        "new": new,
        "dropped": dropped,
        "newly_cited_records": sorted(current_ids - before_ids),
    }
