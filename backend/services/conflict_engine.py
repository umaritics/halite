"""
conflict_engine.py — Conflict detection and adjudication for the maintenance domain.

Public API:
    find_candidate_pairs(graph_repo, record_id, max_candidates) -> list[dict]
    classify_conflict(groq_service, new_record, prior_record) -> dict
    adjudicate(new_record, prior_record, classification, adapter) -> dict
    score_confidence(signals) -> float
    route(record, confidence, threshold) -> str
    process_record(graph_repo, groq_service, adapter, record_id, threshold,
                   allow_stub=False) -> dict

§7 guard: process_record raises RuntimeError if groq_service.is_live is False
and allow_stub is False.  Unit tests pass allow_stub=True.

§5 — confidence threshold: default MAINT_CONFIDENCE_THRESHOLD = 0.72
Provisional — must be re-calibrated after T7 evaluation.
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Candidate pairing weights — ONE dict, ONE comment per weight.
# Change here; nowhere else.
# ---------------------------------------------------------------------------
PAIR_WEIGHTS: dict[str, int] = {
    "same_part_name": 3,   # Same PartName → strong match signal
    "same_jasc_code": 2,   # Same JASCCode (ATA chapter) → probable same system
    "same_part_location": 1,  # Same PartLocation → moderate signal
    "within_30_days": 1,   # DifficultyDate within 30 days → temporal proximity
}

# ---------------------------------------------------------------------------
# Confidence scoring weights — one weight per signal, one comment per line.
# ---------------------------------------------------------------------------
WEIGHTS_WITH_CITATION: dict[str, float] = {
    "explicit_supersession_language": 0.40,  # "SUPPLEMENTAL REPORT FOR" in text — strongest
    "classification_supersedes": 0.20,        # LLM says 'supersedes' or 'partial_supersedes'
    "recency_advantage": 0.15,                # New record is clearly later by date
    "authority_advantage": 0.10,              # New record from more authoritative source
    "part_agreement": 0.10,                   # Same PartName and JASCCode
    "proximity_bonus": 0.05,                  # DifficultyDate within 30 days
}

WEIGHTS_NO_CITATION: dict[str, float] = {
    "explicit_supersession_language": 0.0,
    "classification_supersedes": 0.35,        # increased weight
    "recency_advantage": 0.25,                # increased weight
    "authority_advantage": 0.15,              # increased weight
    "part_agreement": 0.15,                   # increased weight
    "proximity_bonus": 0.10,                  # increased weight
}

# Default threshold — provisional, pending T7 calibration.
# Documented as provisional in the final report; do not present as tuned.
MAINT_CONFIDENCE_THRESHOLD: float = float(
    os.environ.get("MAINT_CONFIDENCE_THRESHOLD", "0.72")
)

# Max candidates to retrieve per record — env-overridable.
MAINT_MAX_CANDIDATES: int = int(
    os.environ.get("MAINT_MAX_CANDIDATES", "25")
)

# Classification labels returned by the LLM
_VALID_LABELS = frozenset(
    ["no_conflict", "scope_disjoint", "supersedes", "partial_supersedes", "contradicts"]
)

# System prompt for conflict classification
_CLASSIFICATION_SYSTEM_PROMPT = """You are a technical conflict classifier for aviation maintenance records.

Given a NEW service record and a PRIOR service record for the same aircraft, classify the relationship.

Respond with a JSON object (no markdown, no explanation) with exactly these keys:
  "label": one of ["no_conflict", "scope_disjoint", "supersedes", "partial_supersedes", "contradicts"]
  "rationale": a single sentence explaining your reasoning (max 60 words)

Definitions:
  no_conflict          — records describe unrelated or compatible maintenance events
  scope_disjoint       — records address different parts/systems despite same aircraft
  supersedes           — new record explicitly updates or closes the prior record
  partial_supersedes   — new record addresses the same issue but only partially resolves it
  contradicts          — records make mutually exclusive claims about the same part/event

Return ONLY the JSON object.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_candidate_pairs(
    graph_repo, record_id: str, max_candidates: int = MAINT_MAX_CANDIDATES
) -> list[dict]:
    """
    Find candidate prior records for the given record_id from the same asset's history.

    Scores each prior record on PAIR_WEIGHTS and returns the top max_candidates.
    Only searches within the same asset's graph-constrained history —
    this is the architectural reason a graph is used (not all-pairs comparison).

    Returns list of dicts with keys: record (dict), score (int).
    """
    # Get the target record
    target = graph_repo.get_service_record(record_id)
    if target is None:
        logger.warning("find_candidate_pairs: record %r not found", record_id)
        return []

    # Find the asset linked to this record
    if graph_repo.is_memory:
        sr_nodes = graph_repo.store._find_nodes("ServiceRecord", record_id=record_id)
        if not sr_nodes:
            return []
        sr_node_id = sr_nodes[0]["id"]
        # Find the asset via ABOUT edge
        asset_id = None
        for edge in graph_repo.store.edges:
            if edge["source"] == sr_node_id and edge["type"] == "ABOUT":
                asset_id = edge["target"]
                break
        if asset_id is None:
            logger.debug("find_candidate_pairs: no asset linked to %r", record_id)
            return []
    else:
        rows = graph_repo.store.run_query(
            """
            MATCH (sr:ServiceRecord {record_id: $rid})-[:ABOUT]->(a:Asset)
            RETURN a.id as asset_id
            """,
            {"rid": record_id},
        )
        if not rows:
            return []
        asset_id = rows[0]["asset_id"]

    # Get the full asset history (ascending by occurred_at)
    history = graph_repo.list_asset_history(asset_id, limit=200)

    # Score each prior record (exclude the target record itself)
    candidates = []
    target_occurred = target.get("occurred_at", "")
    target_submitted = target.get("submitted_at", "")

    for prior in history:
        if prior.get("record_id") == record_id:
            continue  # skip self
        # Only look at records that are older than the target, or same day but submitted earlier
        prior_occurred = prior.get("occurred_at", "")
        if prior_occurred > target_occurred:
            continue
        if prior_occurred == target_occurred:
            if prior.get("submitted_at", "") >= target_submitted:
                continue

        score = 0
        # same_part_name
        if (
            target.get("part_name", "").strip().lower()
            and target.get("part_name", "").strip().lower()
            == prior.get("part_name", "").strip().lower()
        ):
            score += PAIR_WEIGHTS["same_part_name"]

        # same_jasc_code
        if (
            target.get("jasc_code", "").strip()
            and target.get("jasc_code", "").strip() == prior.get("jasc_code", "").strip()
        ):
            score += PAIR_WEIGHTS["same_jasc_code"]

        # same_part_location
        if (
            target.get("part_location", "").strip().lower()
            and target.get("part_location", "").strip().lower()
            == prior.get("part_location", "").strip().lower()
        ):
            score += PAIR_WEIGHTS["same_part_location"]

        # within_30_days
        try:
            d1 = datetime.strptime(prior["occurred_at"], "%Y-%m-%d")
            d2 = datetime.strptime(target_occurred, "%Y-%m-%d")
            if abs((d2 - d1).days) <= 30:
                score += PAIR_WEIGHTS["within_30_days"]
        except (ValueError, KeyError):
            pass

        candidates.append({"record": prior, "score": score})

    # Sort descending by score, then descending by occurred_at (most recent first)
    candidates.sort(key=lambda c: (-c["score"], c["record"].get("occurred_at", "")), reverse=False)
    candidates.sort(key=lambda c: -c["score"])

    result = candidates[:max_candidates]
    logger.info(
        "find_candidate_pairs: record=%r asset=%r history=%d candidates=%d",
        record_id, asset_id, len(history), len(result),
    )
    return result


def classify_conflict(groq_service, new_record: dict, prior_record: dict) -> dict:
    """
    Ask the LLM to classify the conflict relationship between two records.

    Returns dict with: label, rationale, parse_failed (bool).
    On parse failure returns label='no_conflict', parse_failed=True.
    Parse failures are counted in process_record, not hidden.
    """
    prompt = (
        f"NEW RECORD (occurred_at={new_record.get('occurred_at', '?')}):\n"
        f"{new_record.get('text', '')[:800]}\n\n"
        f"PRIOR RECORD (occurred_at={prior_record.get('occurred_at', '?')}):\n"
        f"{prior_record.get('text', '')[:800]}"
    )
    raw = groq_service.extract_json(prompt=prompt, system_prompt=_CLASSIFICATION_SYSTEM_PROMPT)
    parsed = _parse_classification(raw)
    return parsed


def _parse_classification(raw: str) -> dict:
    """Parse LLM JSON response.  On failure return no_conflict with parse_failed=True."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    try:
        data = json.loads(text)
        label = data.get("label", "no_conflict")
        if label not in _VALID_LABELS:
            logger.warning("Invalid label %r from LLM, defaulting to no_conflict", label)
            label = "no_conflict"
        return {
            "label": label,
            "rationale": data.get("rationale", ""),
            "parse_failed": False,
        }
    except json.JSONDecodeError as exc:
        logger.warning("classify_conflict parse failure: %s | raw=%r", exc, text[:200])
        return {
            "label": "no_conflict",
            "rationale": "",
            "parse_failed": True,
        }


def adjudicate(new_record: dict, prior_record: dict, classification: dict, adapter) -> dict:
    """
    Evidence-based adjudication — takes no user input.

    Evidence considered:
      1. Recency:         newer occurred_at favours the new record
      2. Source authority: adapter.source_authority() determines weight
      3. Explicit supersession language in new_record.text
      4. Part/JASC agreement
      5. Days between records

    Returns dict with: action (str), evidence (list[str]), days_between (int|None).
    """
    evidence = []

    new_occurred = new_record.get("occurred_at", "")
    prior_occurred = prior_record.get("occurred_at", "")

    # Recency
    days_between = None
    try:
        d_new = datetime.strptime(new_occurred, "%Y-%m-%d")
        d_prior = datetime.strptime(prior_occurred, "%Y-%m-%d")
        days_between = (d_new - d_prior).days
        if days_between > 0:
            evidence.append(f"new record is {days_between} days later")
        elif days_between < 0:
            evidence.append(f"new record is {abs(days_between)} days EARLIER (unusual)")
    except ValueError:
        evidence.append("could not parse dates for recency comparison")

    # Authority
    new_auth = adapter.source_authority(new_record)
    prior_auth = adapter.source_authority(prior_record)
    if new_auth >= prior_auth:
        evidence.append(f"authority: new={new_auth}, prior={prior_auth} (new >= prior)")
    else:
        evidence.append(f"authority: new={new_auth}, prior={prior_auth} (prior wins on authority)")

    # Explicit supersession language
    new_text = new_record.get("text", "").upper()
    has_explicit = "SUPPLEMENTAL REPORT FOR" in new_text
    if has_explicit:
        evidence.append("explicit 'SUPPLEMENTAL REPORT FOR' citation found")

    # Part agreement
    same_part = (
        new_record.get("part_name", "").strip().lower()
        == prior_record.get("part_name", "").strip().lower()
        and new_record.get("part_name", "").strip()
    )
    same_jasc = (
        new_record.get("jasc_code", "").strip()
        == prior_record.get("jasc_code", "").strip()
        and new_record.get("jasc_code", "").strip()
    )
    if same_part:
        evidence.append(f"same part_name: {new_record.get('part_name', '')!r}")
    if same_jasc:
        evidence.append(f"same jasc_code: {new_record.get('jasc_code', '')!r}")

    # Determine action
    label = classification.get("label", "no_conflict")
    if has_explicit or label == "supersedes":
        action = "supersedes"
    elif label == "partial_supersedes":
        action = "partial_supersedes"
    elif label == "contradicts":
        action = "contradicts"
    else:
        action = "no_action"

    return {
        "action": action,
        "evidence": evidence,
        "days_between": days_between,
    }


def score_confidence(signals: dict) -> float:
    """
    Compute a confidence score in [0, 1] from evidence signals.
    """
    score = 0.0
    has_citation = signals.get("explicit_supersession_language", False)
    weights = WEIGHTS_WITH_CITATION if has_citation else WEIGHTS_NO_CITATION
    
    for key, weight in weights.items():
        if signals.get(key, False):
            score += weight
    # Clamp to [0, 1]
    return max(0.0, min(1.0, score))


def route(record: dict, confidence: float, threshold: float) -> str:
    """
    Route a record to auto_accepted or needs_review based on confidence.

    confidence >= threshold → auto_accepted
    confidence <  threshold → needs_review

    Returns one of: 'auto_accepted', 'needs_review'
    """
    return "auto_accepted" if confidence >= threshold else "needs_review"


def process_record(
    graph_repo,
    groq_service,
    adapter,
    record_id: str,
    threshold: float = MAINT_CONFIDENCE_THRESHOLD,
    allow_stub: bool = False,
) -> dict:
    """
    Full conflict-detection pipeline for a single ServiceRecord.

    §7 guard: raises RuntimeError if groq_service.is_live is False
    and allow_stub is False.  Unit tests MUST pass allow_stub=True.

    Returns:
      record_id, candidates_considered (int), best_prior (dict|None),
      classification (dict|None), adjudication (dict|None),
      signals (dict), confidence (float), route (str),
      parse_failures (int), status_applied (str)
    """
    # §7: refuse to run with canned responses in production context
    if not allow_stub and not groq_service.is_live:
        raise RuntimeError(
            "process_record: groq_service is not live (is_live=False). "
            "Running with a canned LLM response would produce meaningless results. "
            "Either configure GROQ_API_KEY or call with allow_stub=True (tests only)."
        )

    parse_failures = 0

    # 1. Find candidates
    candidates = find_candidate_pairs(graph_repo, record_id, max_candidates=MAINT_MAX_CANDIDATES)
    target = graph_repo.get_service_record(record_id)
    if target is None:
        raise ValueError(f"process_record: record {record_id!r} not found in graph")

    if not candidates:
        return {
            "record_id": record_id,
            "candidates_considered": 0,
            "best_prior": None,
            "classification": None,
            "adjudication": None,
            "signals": {},
            "confidence": 0.0,
            "route": "auto_accepted",
            "parse_failures": 0,
            "status_applied": "auto_accepted",
        }

    # 2. Classify against the top candidate
    best = candidates[0]["record"]
    classification = classify_conflict(groq_service, target, best)
    if classification.get("parse_failed"):
        parse_failures += 1
        logger.warning("process_record: parse failure for record %r", record_id)

    # 3. Adjudicate
    adjudication_result = adjudicate(target, best, classification, adapter)

    # 4. Build signals dict
    new_occurred = target.get("occurred_at", "")
    prior_occurred = best.get("occurred_at", "")
    days_between = adjudication_result.get("days_between")

    new_text_upper = target.get("text", "").upper()
    signals = {
        "explicit_supersession_language": "SUPPLEMENTAL REPORT FOR" in new_text_upper,
        "classification_supersedes": classification.get("label") in (
            "supersedes", "partial_supersedes"
        ),
        "recency_advantage": (
            days_between is not None and days_between > 0
        ),
        "authority_advantage": (
            adapter.source_authority(target) >= adapter.source_authority(best)
        ),
        "part_agreement": (
            bool(target.get("part_name", "").strip())
            and target.get("part_name", "").strip().lower()
            == best.get("part_name", "").strip().lower()
            and bool(target.get("jasc_code", "").strip())
            and target.get("jasc_code", "").strip() == best.get("jasc_code", "").strip()
        ),
        "proximity_bonus": (days_between is not None and 0 < days_between <= 30),
    }

    # 5. Score confidence
    confidence = score_confidence(signals)

    # 6. Route
    routing_decision = route(target, confidence, threshold)

    # 7. Apply to graph on confirmed supersession
    action = adjudication_result.get("action")
    if routing_decision == "auto_accepted" and action in ("supersedes", "partial_supersedes"):
        graph_repo.link_record_supersedes(
            new_record_id=record_id,
            old_record_id=best["record_id"],
            scope=action,
            confidence=confidence,
            rationale=classification.get("rationale", ""),
        )
        graph_repo.update_service_record(best["record_id"], {"status": "superseded"})
        status_applied = "auto_accepted"
    else:
        status_applied = routing_decision

    graph_repo.update_service_record(record_id, {"status": status_applied, "confidence": confidence})

    return {
        "record_id": record_id,
        "candidates_considered": len(candidates),
        "best_prior": best,
        "classification": classification,
        "adjudication": adjudication_result,
        "signals": signals,
        "confidence": confidence,
        "route": routing_decision,
        "parse_failures": parse_failures,
        "status_applied": status_applied,
    }
