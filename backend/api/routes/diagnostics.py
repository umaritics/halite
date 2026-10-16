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
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.deps import get_graph_repo, get_groq_service, get_settings
from services.citation_validation import validate_citations
from services.diagnostic_retrieval import (
    build_diagnostic_context,
    build_copilot_context,
    rank_diagnostic_checks,
    rank_copilot_checks,
    ranking_delta,
)

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


class CaseState(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    checks_done: list[str] = Field(default_factory=list)
    ruled_out: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class CopilotTurnRequest(BaseModel):
    session_id: Optional[str] = None
    asset_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=4000)
    case_state: Optional[CaseState] = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


# ---------------------------------------------------------------------------
# Cache helpers (reuse pattern from conflict_engine.py)
# ---------------------------------------------------------------------------

def _cache_path() -> Path:
    from config import settings
    return Path(settings.MAINT_DATA_DIR) / "diag_cache" / "cache.json"


def _cache_key(asset_id: str, symptom: str, model: str) -> str:
    normalised = re.sub(r"\s+", " ", symptom.strip().lower())
    raw = f"{asset_id}|{normalised}|{model}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_cache() -> dict:
    p = _cache_path()
    if p.exists():
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    p = _cache_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError as exc:
        logger.warning("Diagnostic cache unavailable; continuing without persistence: %s", exc)


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


_CASE_FIELDS = ("symptoms", "observations", "checks_done", "ruled_out", "open_questions")


def _dedupe_strings(values: list, limit: int = 30) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _normalise_case_state(value: dict | None) -> dict:
    value = value or {}
    return {field: _dedupe_strings(value.get(field, [])) for field in _CASE_FIELDS}


def _parse_json_object(raw: str) -> dict:
    cleaned = re.sub(r"^```[a-z]*\n?", "", (raw or "").strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip())
    parsed = json.loads(cleaned, strict=False)
    if not isinstance(parsed, dict):
        raise ValueError("model response was not a JSON object")
    return parsed


def _extract_case_facts(groq_service, current: dict, message: str) -> tuple[dict, list[str]]:
    """Extract only new facts, with a deterministic raw-text fallback."""
    warnings = []
    prompt = (
        "Extract NEW maintenance case facts from the technician message. "
        "Return strict JSON with exactly these string-array keys: symptoms, observations, "
        "checks_done, ruled_out, open_questions. Do not repeat facts already in CURRENT_STATE.\n"
        f"CURRENT_STATE: {json.dumps(current, ensure_ascii=False)}\n"
        f"MESSAGE: {message}"
    )
    try:
        raw = groq_service.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="Return only strict JSON. Do not add markdown.",
            max_tokens=1200,
        )
        parsed = _parse_json_object(raw)
        additions = {}
        for field in _CASE_FIELDS:
            value = parsed.get(field, [])
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError(f"invalid case-state field: {field}")
            additions[field] = _dedupe_strings(value)
        return additions, warnings
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        warnings.append(f"Case extraction failed validation; the raw message was retained: {exc}")
        return {
            "symptoms": [message],
            "observations": [],
            "checks_done": [],
            "ruled_out": [],
            "open_questions": [],
        }, warnings


def _merge_case_state(current: dict, additions: dict) -> dict:
    return {
        field: _dedupe_strings([*current.get(field, []), *additions.get(field, [])])
        for field in _CASE_FIELDS
    }


def _asset_exists(graph_repo, asset_id: str) -> bool:
    return any(str(asset.get("id")) == asset_id for asset in graph_repo.list_assets_with_counts())


def _record_evidence(record: dict) -> dict:
    status = record.get("status", "")
    return {
        "record_id": str(record.get("record_id", record.get("id", ""))),
        "asset_id": record.get("asset_id") or record.get("asset_key") or "",
        "occurred_at": record.get("occurred_at", ""),
        "part_name": record.get("part_name", ""),
        "status": status,
        "is_superseded": bool(record.get("is_superseded")) or status == "superseded",
        "text": record.get("text", ""),
    }


def _collect_evidence(context: dict, ranked: list[dict], extra: list[dict] | None = None) -> list[dict]:
    records = [*(extra or []), *context.get("asset_history", []), *context.get("fleet_matches", [])]
    by_id = {
        str(record.get("record_id", record.get("id", ""))): record
        for record in records
        if record.get("record_id", record.get("id"))
    }
    ordered_ids = []
    for item in ranked[:10]:
        ordered_ids.extend(item.get("evidence_record_ids", []))
    ordered_ids = [
        *[str(r.get("record_id", r.get("id", ""))) for r in (extra or [])],
        *ordered_ids,
        *[
            str(r.get("record_id", r.get("id", "")))
            for r in records
            if r.get("is_superseded") or r.get("status") == "superseded"
        ],
    ]
    result = []
    seen = set()
    for record_id in ordered_ids:
        if record_id in seen or record_id not in by_id:
            continue
        seen.add(record_id)
        result.append(_record_evidence(by_id[record_id]))
        if len(result) >= 20:
            break
    return result


def _select_report_records(graph_repo, asset_id: Optional[str], message: str) -> list[dict]:
    """Deterministically select explicit IDs or asset/date/topic records."""
    explicit_ids = re.findall(r"\b(?:record\s+)?([A-Z]{2,8}\d{5,})\b", message.upper())
    if explicit_ids:
        by_id = {
            str(record.get("record_id", record.get("id", ""))): record
            for record in graph_repo.get_service_records_by_ids(_dedupe_strings(explicit_ids, limit=20))
        }
        return [by_id[rid] for rid in _dedupe_strings(explicit_ids, limit=20) if rid in by_id]

    report_words = {"summarize", "summarise", "explain", "compare", "history", "records", "record"}
    lowered_words = set(re.findall(r"[a-z0-9]+", message.lower()))
    if not lowered_words.intersection(report_words) or not asset_id:
        return []

    records = graph_repo.list_asset_history_recent(asset_id, limit=30)
    years = sorted({int(year) for year in re.findall(r"\b(20\d{2})\b", message)})
    if years:
        records = [
            record for record in records
            if any(str(record.get("occurred_at", "")).startswith(str(year)) for year in years)
        ]
    stop = report_words | {"this", "aircraft", "for", "the", "and", "from", "to", "in", "during", "of"}
    keywords = sorted(word for word in lowered_words - stop if len(word) >= 4 and not word.isdigit())
    if keywords:
        matched = [
            record for record in records
            if any(
                keyword in f"{record.get('part_name', '')} {record.get('text', '')}".lower()
                for keyword in keywords
            )
        ]
        if matched:
            records = matched
    return records[:20]


def _limit_to_one_question(text: str) -> str:
    seen_question = False
    output = []
    for char in text:
        if char == "?":
            if seen_question:
                output.append(".")
            else:
                output.append(char)
                seen_question = True
        else:
            output.append(char)
    return "".join(output)

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

    # 4. Rank components (pure graph — no LLM; see rank_diagnostic_checks)
    ranked = rank_diagnostic_checks(context)

    # 5. Build prompt and call LLM only to phrase the answer
    prompt = _build_prompt(context, ranked)
    try:
        raw_llm = groq_service.chat(
            [{"role": "user", "content": prompt}],
            system_prompt=(
                "You are a maintenance diagnostic assistant. "
                "Respond ONLY with valid JSON as instructed. "
                "Never invent record IDs."
            ),
            max_tokens=2048,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # 6. Parse LLM JSON
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"^```[a-z]*\n?", "", raw_llm.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip())
        llm_json = json.loads(cleaned, strict=False)
    except Exception:
        llm_json = {"explanation": raw_llm, "rare_cases": [], "warnings": []}

    # 7. Citation validation — mandatory
    explanation_text = llm_json.get("explanation", raw_llm)
    if explanation_text is None or not str(explanation_text).strip():
        raise HTTPException(
            status_code=503,
            detail="The language model returned an empty explanation; no blank diagnosis was emitted.",
        )
    citation_result = validate_citations(explanation_text, graph_repo)

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
# Endpoint: /copilot/turn (stateless multi-turn diagnostic investigation)
# ---------------------------------------------------------------------------

@router.post("/copilot/turn")
def copilot_turn(
    req: CopilotTurnRequest,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
):
    """Advance a stateless, evidence-grounded diagnostic case by one turn."""
    if req.asset_id and not _asset_exists(graph_repo, req.asset_id):
        raise HTTPException(status_code=404, detail=f"Unknown asset_id={req.asset_id}")

    previous_state = _normalise_case_state(
        req.case_state.model_dump() if req.case_state else None
    )
    previous_context = build_copilot_context(graph_repo, req.asset_id, previous_state)
    previous_ranked = (
        rank_copilot_checks(previous_context, previous_state["ruled_out"])
        if any(previous_state[field] for field in _CASE_FIELDS)
        else []
    )

    warnings: list[str] = []
    llm_status = "available"
    if not groq_service.is_live:
        additions = {
            "symptoms": [req.message],
            "observations": [],
            "checks_done": [],
            "ruled_out": [],
            "open_questions": [],
        }
        warnings.append("Language model unavailable; raw message retained in case state.")
        llm_status = "unavailable"
    else:
        try:
            additions, extraction_warnings = _extract_case_facts(
                groq_service, previous_state, req.message
            )
            warnings.extend(extraction_warnings)
        except Exception as exc:
            logger.warning("Copilot fact extraction unavailable: %s", exc)
            additions = {
                "symptoms": [req.message],
                "observations": [],
                "checks_done": [],
                "ruled_out": [],
                "open_questions": [],
            }
            warnings.append(f"Language model unavailable during case extraction: {exc}")
            llm_status = "unavailable"

    case_state = _merge_case_state(previous_state, additions)
    context = build_copilot_context(graph_repo, req.asset_id, case_state)
    ranked = rank_copilot_checks(context, case_state["ruled_out"])
    delta = ranking_delta(previous_ranked, ranked)
    selected_records = _select_report_records(graph_repo, req.asset_id, req.message)
    evidence = _collect_evidence(context, ranked, selected_records)

    if not ranked and not selected_records:
        warnings.append("No relevant service history was found for the accumulated case.")

    reply = None
    citation_result = {"valid": [], "invalid": [], "flagged_text": ""}
    if llm_status != "unavailable":
        if not evidence:
            reply = "No relevant service history was found for the accumulated case."
            llm_status = "not_needed"
        else:
            report_mode = bool(selected_records)
            evidence_payload = [
                {
                    "record_id": item["record_id"],
                    "asset_id": item["asset_id"],
                    "occurred_at": item["occurred_at"],
                    "part_name": item["part_name"],
                    "status": item["status"],
                    "is_superseded": item["is_superseded"],
                    "text": item["text"][:700],
                }
                for item in evidence
            ]
            prompt = (
                "Write the next diagnostic-copilot reply using ONLY EVIDENCE below. "
                "Cite record IDs exactly. Do not invent procedures, root causes, or facts. "
                "Superseded records are historical context only: label them and NEVER recommend acting on them. "
                "Ask at most ONE clarifying question, only when key information is missing. "
                "Describe ranking changes from RANKING_DELTA. "
                + (
                    "This is a report-help request. Use headings 'Records state' and 'Interpretation'. "
                    "Say explicitly when root cause or another requested fact is not in the data. "
                    if report_mode else ""
                )
                + f"\nTECHNICIAN_MESSAGE: {req.message}"
                + f"\nCASE_STATE: {json.dumps(case_state, ensure_ascii=False)}"
                + f"\nRANKED_CHECKS: {json.dumps(ranked[:10], ensure_ascii=False)}"
                + f"\nRANKING_DELTA: {json.dumps(delta, ensure_ascii=False)}"
                + f"\nEVIDENCE: {json.dumps(evidence_payload, ensure_ascii=False)}"
            )
            try:
                raw_reply = groq_service.chat(
                    [{"role": "user", "content": prompt}],
                    system_prompt=(
                        "You are an evidence-grounded aircraft maintenance assistant. "
                        "Never present a superseded record as a recommendation."
                    ),
                    max_tokens=2400,
                )
                if raw_reply is None or not str(raw_reply).strip():
                    raise RuntimeError("The language model returned empty content.")
                raw_reply = _limit_to_one_question(str(raw_reply).strip())
                citation_result = validate_citations(raw_reply, graph_repo)

                allowed_ids = {item["record_id"] for item in evidence}
                out_of_context = [
                    rid for rid in citation_result["valid"] if rid not in allowed_ids
                ]
                if out_of_context:
                    citation_result["valid"] = [
                        rid for rid in citation_result["valid"] if rid in allowed_ids
                    ]
                    citation_result["invalid"] = _dedupe_strings(
                        [*citation_result["invalid"], *out_of_context]
                    )
                    flagged = citation_result["flagged_text"]
                    for record_id in out_of_context:
                        flagged = flagged.replace(record_id, f"[UNVERIFIED:{record_id}]")
                    citation_result["flagged_text"] = flagged
                reply = citation_result["flagged_text"]
            except Exception as exc:
                logger.warning("Copilot reply unavailable: %s", exc)
                warnings.append(f"Language model unavailable: {exc}")
                llm_status = "unavailable"
                reply = None

    return {
        "session_id": req.session_id or str(uuid.uuid4()),
        "reply": reply,
        "case_state": case_state,
        "ranked_checks": ranked[:10],
        "ranking_delta": delta,
        "evidence": evidence,
        "citation_validation": {
            "valid_ids": citation_result["valid"],
            "invalid_ids": citation_result["invalid"],
            "all_valid": len(citation_result["invalid"]) == 0,
        },
        "llm_status": llm_status,
        "warnings": _dedupe_strings(warnings),
    }


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

    citation_result = validate_citations(raw, graph_repo)

    return {
        "reply":       citation_result["flagged_text"],
        "citations":   citation_result["valid"],
        "invalid_ids": citation_result["invalid"],
        "context_size": context_size,
    }
