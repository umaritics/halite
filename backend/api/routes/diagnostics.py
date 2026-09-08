"""
backend/api/routes/diagnostics.py

G3: Diagnostic endpoints for the maintenance domain.

Routes:
  POST /api/maintenance/diagnose  — ranked inspection order with citations
  POST /api/maintenance/chat      — grounded conversational reply

Hard requirements:
  - Citations are mandatory. Every record_id in LLM output must exist in graph.
    Non-existent IDs are dropped with a flag.
  - Fail loud: raise if groq_service.is_live is False (unless cache hit exists).
  - Cache: keyed on (asset_id, normalised_symptom, model) in backend/data/maintenance/diag_cache.json
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_graph_repo, get_groq_service, get_settings
from services.diagnostic_retrieval import build_diagnostic_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["diagnostics"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class DiagnoseRequest(BaseModel):
    asset_id: str
    symptom_text: str


class ChatRequest(BaseModel):
    message: str
    asset_id: Optional[str] = None
    history: Optional[list[dict]] = None


# ---------------------------------------------------------------------------
# Cache helpers (reuse pattern from conflict_engine.py)
# ---------------------------------------------------------------------------

def _cache_dir() -> Path:
    from config import settings
    d = Path(settings.MAINT_DATA_DIR) / "diag_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(asset_id: str, symptom: str, model: str) -> str:
    normalised = re.sub(r"\s+", " ", symptom.strip().lower())
    raw = f"{asset_id}|{normalised}|{model}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_cache() -> dict:
    p = _cache_dir() / "cache.json"
    if p.exists():
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    p = _cache_dir() / "cache.json"
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error("Failed to write diag cache: %s", e)


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------

# Pattern: uppercase letters+digits sequences that look like FAA SDR IDs
_RECORD_ID_RE = re.compile(r"\b([A-Z]{2,6}[\d]{6,})\b")


def _validate_citations(text: str, graph_repo) -> dict:
    """
    Extract all record-ID-like tokens from LLM output and verify each exists
    in the graph. Returns {valid: [...], invalid: [...], flagged_text: str}.
    """
    found = list(set(_RECORD_ID_RE.findall(text)))
    valid = []
    invalid = []
    for rid in found:
        rec = graph_repo.get_service_record(rid)
        if rec:
            valid.append(rid)
        else:
            invalid.append(rid)

    # Build flagged version: mark invalid IDs
    flagged = text
    for rid in invalid:
        flagged = flagged.replace(rid, f"[UNVERIFIED:{rid}]")

    return {"valid": valid, "invalid": invalid, "flagged_text": flagged}


# ---------------------------------------------------------------------------
# Ranking logic (graph-derived, not LLM-derived)
# ---------------------------------------------------------------------------

def _rank_components(context: dict) -> list[dict]:
    """
    Produce a ranked inspection order from the graph context.

    Ranking signals (all from real records):
      1. Prior resolution frequency: how often has a component been the
         corrective action on this asset or fleet?
      2. Recency on this asset: components that appear in recent history
         are ranked higher.
      3. Fleet match score: components with high fleet similarity scores.

    No LLM involved here — the ranking is computed from structure.
    """
    component_scores: dict[str, dict] = {}

    def _add(part: str, weight: float, source: str, record_id: str):
        if not part or part.upper() in ("UNKNOWN", ""):
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
        component_scores[key]["score"] += weight
        component_scores[key]["evidence_count"] += 1
        component_scores[key]["evidence_record_ids"].append(record_id)
        if source not in component_scores[key]["sources"]:
            component_scores[key]["sources"].append(source)

    # Asset history: higher weight for recent non-superseded records
    for i, rec in enumerate(context["asset_history"]):
        recency_weight = 1.0 / (i + 1)  # newest (i=0) → weight 1.0
        superseded_penalty = 0.3 if rec.get("is_superseded") else 1.0
        _add(rec.get("part_name", ""),
             recency_weight * superseded_penalty * 0.4,
             "asset_history",
             rec["record_id"])

    # Fleet matches: scored by similarity
    for rec in context["fleet_matches"]:
        fleet_score = rec.get("score", 0.1)
        superseded_penalty = 0.3 if rec.get("is_superseded") else 1.0
        _add(rec.get("part_name", ""),
             fleet_score * superseded_penalty * 0.6,
             "fleet_match",
             rec["record_id"])

    # Sort by score descending
    ranked = sorted(component_scores.values(), key=lambda x: x["score"], reverse=True)
    for i, item in enumerate(ranked):
        item["rank"] = i + 1
        item["score"] = round(item["score"], 4)
    return ranked


def _build_prompt(context: dict, ranked: list[dict]) -> str:
    """Build the LLM prompt from graph context + pre-computed ranking."""
    asset_id = context["asset_id"]
    symptom = context["symptom_text"]
    n_asset = context["context_size"]["asset_records"]
    n_fleet = context["context_size"]["fleet_records"]
    n_assets = context["context_size"]["fleet_assets"]

    ranked_str = "\n".join(
        f"  {r['rank']}. {r['part_name']} "
        f"(evidence_count={r['evidence_count']}, "
        f"record_ids={r['evidence_record_ids'][:3]})"
        for r in ranked[:5]
    )

    fleet_str = "\n".join(
        f"  [{r['record_id']}] {r.get('part_name','')} "
        f"- {r.get('text','')[:80]} "
        f"({'SUPERSEDED' if r.get('is_superseded') else 'active'})"
        for r in context["fleet_matches"][:5]
    )

    history_str = "\n".join(
        f"  [{r['record_id']}] {r.get('occurred_at','')} "
        f"{r.get('part_name','')} "
        f"({'SUPERSEDED' if r.get('is_superseded') else r.get('status','')})"
        for r in context["asset_history"][:5]
    )

    return (
        f"You are a maintenance diagnostic assistant. A technician has reported:\n"
        f'Symptom: "{symptom}"\n'
        f"Asset: {asset_id}\n\n"
        f"The graph has pre-ranked the most likely components:\n{ranked_str}\n\n"
        f"Recent asset history (newest first):\n{history_str}\n\n"
        f"Fleet-wide matches from {n_assets} other aircraft:\n{fleet_str}\n\n"
        f"CONTEXT: Answered from {n_asset} records on this asset and "
        f"{n_fleet} fleet-wide matches across {n_assets} assets.\n\n"
        f"Instructions:\n"
        f"1. Explain in plain language WHY each component is ranked there, "
        f"citing ONLY record IDs from the lists above.\n"
        f"2. Highlight any fleet cases that provide rare prior evidence.\n"
        f"3. Mark clearly any superseded records — do not recommend acting on them.\n"
        f"4. Do NOT invent record IDs. Use ONLY the IDs provided above.\n"
        f"5. Respond in JSON: "
        f'{{"explanation": "...", "rare_cases": ["record_id", ...], '
        f'"warnings": ["..."]}}'
    )


# ---------------------------------------------------------------------------
# Endpoint: /diagnose
# ---------------------------------------------------------------------------

@router.post("/diagnose")
def diagnose(
    req: DiagnoseRequest,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
):
    """
    POST /api/maintenance/diagnose
    Body: {asset_id, symptom_text}
    Returns: {ranked_checks, evidence, rare_cases, context_size, citation_validation}
    """
    # 1. Cache check
    cache = _load_cache()
    ck = _cache_key(req.asset_id, req.symptom_text, groq_service.model)
    in_test = "PYTEST_CURRENT_TEST" in os.environ

    if ck in cache and not in_test:
        logger.info("diagnose: CACHE HIT %s", ck)
        return cache[ck]

    # 2. Fail loud if LLM not live (no cache)
    if not groq_service.is_live:
        raise HTTPException(
            status_code=503,
            detail=(
                "Groq LLM is not configured (is_live=False). "
                "Cannot produce a diagnostic without a live model. "
                "Set GROQ_API_KEY in .env and restart."
            ),
        )

    # 3. Build context (pure graph — no LLM)
    t0 = time.time()
    context = build_diagnostic_context(graph_repo, req.asset_id, req.symptom_text)

    if not context["asset_history"]:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for asset_id={req.asset_id}. "
                   "Check the ID or ensure the corpus is ingested.",
        )

    # 4. Rank components (pure graph — no LLM)
    ranked = _rank_components(context)

    # 5. Build prompt and call LLM only to phrase the answer
    prompt = _build_prompt(context, ranked)
    raw_llm = groq_service.chat(
        [{"role": "user", "content": prompt}],
        system_prompt=(
            "You are a maintenance diagnostic assistant. "
            "Respond ONLY with valid JSON as instructed. "
            "Never invent record IDs."
        ),
        max_tokens=1000,
    )

    # 6. Parse LLM JSON
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"^```[a-z]*\n?", "", raw_llm.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip())
        llm_json = json.loads(cleaned)
    except Exception:
        llm_json = {"explanation": raw_llm, "rare_cases": [], "warnings": []}

    # 7. Citation validation — mandatory
    explanation_text = llm_json.get("explanation", raw_llm)
    citation_result = _validate_citations(explanation_text, graph_repo)

    # 8. Collect evidence records
    all_cited_ids = citation_result["valid"]
    evidence = []
    for rid in all_cited_ids[:10]:
        rec = graph_repo.get_service_record(rid)
        if rec:
            evidence.append({
                "record_id":    rid,
                "asset_id":     rec.get("asset_key", ""),
                "occurred_at":  rec.get("occurred_at", ""),
                "part_name":    rec.get("part_name", ""),
                "status":       rec.get("status", ""),
                "is_superseded": rec.get("status") == "superseded",
            })

    # 9. Rare cases
    rare_case_ids = llm_json.get("rare_cases", [])
    rare_cases = []
    for rid in rare_case_ids:
        rec = graph_repo.get_service_record(rid)
        if rec:
            rare_cases.append({
                "record_id":   rid,
                "asset_id":    rec.get("asset_key", ""),
                "occurred_at": rec.get("occurred_at", ""),
                "part_name":   rec.get("part_name", ""),
                "text":        rec.get("text", "")[:200],
            })

    elapsed = round(time.time() - t0, 2)

    result = {
        "asset_id":        req.asset_id,
        "symptom_text":    req.symptom_text,
        "ranked_checks":   ranked[:10],
        "evidence":        evidence,
        "rare_cases":      rare_cases,
        "explanation":     citation_result["flagged_text"],
        "context_size":    {
            **context["context_size"],
            "wall_clock_s": elapsed,
        },
        "citation_validation": {
            "valid_ids":   citation_result["valid"],
            "invalid_ids": citation_result["invalid"],
            "all_valid":   len(citation_result["invalid"]) == 0,
        },
        "warnings": llm_json.get("warnings", []),
    }

    # 10. Cache result
    if not in_test:
        cache[ck] = result
        _save_cache(cache)

    return result


# ---------------------------------------------------------------------------
# Endpoint: /chat (grounded conversational reply)
# ---------------------------------------------------------------------------

@router.post("/chat")
def maint_chat(
    req: ChatRequest,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
):
    """
    POST /api/maintenance/chat
    Body: {message, asset_id?, history?}
    Returns: {reply, citations, context_size}
    """
    if not groq_service.is_live:
        raise HTTPException(
            status_code=503,
            detail="Groq LLM is not configured. Cannot answer maintenance chat.",
        )

    # Build context if asset_id provided
    context_str = ""
    context_size = {}
    if req.asset_id:
        context = build_diagnostic_context(graph_repo, req.asset_id, req.message)
        context_size = context["context_size"]
        # Compact context for the chat prompt
        history_lines = [
            f"[{r['record_id']}] {r.get('occurred_at','')} "
            f"{r.get('part_name','')} ({r.get('status','')})"
            for r in context["asset_history"][:10]
        ]
        fleet_lines = [
            f"[{r['record_id']}] {r.get('part_name','')} - {r.get('text','')[:60]}"
            for r in context["fleet_matches"][:5]
        ]
        context_str = (
            f"Asset history (newest first):\n"
            + "\n".join(history_lines)
            + "\nFleet matches:\n"
            + "\n".join(fleet_lines)
        )

    # Build message list
    messages = []
    for h in (req.history or []):
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})

    user_msg = req.message
    if context_str:
        user_msg = f"{context_str}\n\nQuestion: {req.message}"
    messages.append({"role": "user", "content": user_msg})

    raw = groq_service.chat(
        messages,
        system_prompt=(
            "You are a maintenance diagnostic assistant. "
            "Answer using ONLY the record IDs provided in the context. "
            "Do not invent record IDs or facts."
        ),
        max_tokens=800,
    )

    citation_result = _validate_citations(raw, graph_repo)

    return {
        "reply":       citation_result["flagged_text"],
        "citations":   citation_result["valid"],
        "invalid_ids": citation_result["invalid"],
        "context_size": context_size,
    }
