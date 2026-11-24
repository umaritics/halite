"""Two kinds of time: when a fault occurred and when the report about it was submitted.

Only submission time says what was known when; occurrence time is the fallback.
"""
from __future__ import annotations

from datetime import date, datetime, timezone


def parse_submitted(value: object) -> datetime | None:
    """Parse a submission timestamp into an aware datetime, or None.

    Raw strings must never be compared: '-05:00' and '+00:00' stamps sort wrongly as text.
    Naive values are taken as UTC so every result is comparable.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text[-1] in "zZ":
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_occurred(value: object) -> date | None:
    """Parse an occurrence date stored as 'YYYY-MM-DD' (ingest) or 'MM/DD/YYYY' (FAA raw)."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def submission_gap_days(new: dict, prior: dict) -> float | None:
    """Days between the two submissions (positive when prior came first), None if unknown."""
    new_at = parse_submitted(new.get("submitted_at"))
    prior_at = parse_submitted(prior.get("submitted_at"))
    if new_at is None or prior_at is None:
        return None
    return (new_at - prior_at).total_seconds() / 86400


def occurrence_gap_days(new: dict, prior: dict) -> int | None:
    """Whole days between the two occurrence dates, None if either is unknown."""
    new_on = parse_occurred(new.get("occurred_at"))
    prior_on = parse_occurred(prior.get("occurred_at"))
    if new_on is None or prior_on is None:
        return None
    return (new_on - prior_on).days


def is_eligible_prior(new: dict, prior: dict) -> bool:
    """True when prior was known before new: submitted strictly earlier.

    Occurrence dates decide only when a submission time is missing on either side,
    because real corrections share their occurrence date. Unknown on both gives False.
    """
    gap = submission_gap_days(new, prior)
    if gap is not None:
        return gap > 0
    occurrence_gap = occurrence_gap_days(new, prior)
    return occurrence_gap is not None and occurrence_gap > 0
