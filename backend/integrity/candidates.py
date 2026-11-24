"""Candidate retrieval as pure functions over plain record dicts.

The benchmark has to rank candidates with the code staging runs, but staging reads
its history from a graph. Moving the filtering, scoring and ordering here lets both
call the same function; the graph lookups stay in the engine.
"""
from __future__ import annotations

from datetime import datetime

from integrity.timeutil import is_eligible_prior, submission_gap_days
from services.conflict_screen import text_overlap_features

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

ORDERINGS = ("legacy", "containment", "submission_gap")


def pair_score(target: dict, prior: dict) -> int:
    """Sum the weights of the graph-pruning signals the two records share."""
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
        d2 = datetime.strptime(target.get("occurred_at", ""), "%Y-%m-%d")
        if abs((d2 - d1).days) <= 30:
            score += PAIR_WEIGHTS["within_30_days"]
    except (ValueError, KeyError):
        pass
    return score


def rank_candidates(
    target: dict,
    history: list[dict],
    *,
    ordering: str = "legacy",
    rejected=(),
    max_candidates: int | None = None,
) -> list[dict]:
    """Return the comparable earlier records of target, best first.

    A prior is dropped when it is the target, was rejected by a reviewer, was not known
    before the target (leakage), or shares no signal with it: sending score-zero pairs to
    the model turns unrelated history into fake candidates.
    """
    if ordering not in ORDERINGS:
        raise ValueError(f"unknown ordering {ordering!r}; expected one of {ORDERINGS}")
    target_id = target.get("record_id") or target.get("id")
    candidates = []
    for prior in history:
        prior_id = prior.get("record_id") or prior.get("id")
        if prior_id == target_id or prior_id in rejected:
            continue
        if not is_eligible_prior(target, prior):
            continue
        score = pair_score(target, prior)
        if score > 0:
            candidates.append({"record": prior, "score": score})

    # Stable deterministic ordering: score DESC, date DESC, record_id ASC.
    candidates.sort(key=lambda c: str(c["record"].get("record_id", "")))
    candidates.sort(key=lambda c: c["record"].get("occurred_at", ""), reverse=True)
    candidates.sort(key=lambda c: c["score"], reverse=True)

    if ordering == "containment":
        for candidate in candidates:
            candidate["screen_features"] = text_overlap_features(target, candidate["record"])
        # Python's stable sort preserves the legacy score/date/id ordering for ties.
        candidates.sort(key=lambda c: c["screen_features"]["containment"], reverse=True)
    elif ordering == "submission_gap":
        def gap_key(candidate):
            gap = submission_gap_days(target, candidate["record"])
            return (gap is None, gap if gap is not None else 0.0)
        candidates.sort(key=gap_key)

    return candidates if max_candidates is None else candidates[:max_candidates]
