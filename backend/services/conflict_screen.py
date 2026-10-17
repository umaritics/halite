"""Deterministic text features for the opt-in conflict-analysis cascade."""
from __future__ import annotations

import html
import re

_ANSWER_KEY = re.compile(
    r"SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*[A-Z0-9]{6,}\s*\)?\s*: ?",
    re.IGNORECASE,
)
_BOILERPLATE = re.compile(
    r"\b(?:AIRCRAFT WAS (?:NOT )?GROUNDED|AN EMERGENCY WAS (?:NOT )?DECLARED(?: DUE TO)?|"
    r"SUPPLEMENTAL REPORT WILL BE SUBMITTED|OPEN|CLOSED)\b",
    re.IGNORECASE,
)
_TOKEN = re.compile(r"[A-Z0-9]+")
_STOPWORDS = frozenset(
    {
        "THE", "AND", "FOR", "FROM", "WITH", "THAT", "THIS", "WERE", "WAS",
        "HAVE", "HAS", "HAD", "IN", "ON", "AT", "TO", "OF", "IS", "A", "AN",
        "AIRCRAFT", "DURING", "FOUND", "PER", "NOT", "DUE",
    }
)

# Text is primary; structured equality bonuses only rescue sparse true pairs.
SCREEN_WEIGHTS = {
    "part_name": 0.30,
    "jasc_code": 0.20,
    "part_location": 0.10,
}


def normalize_value(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def meaningful_tokens(text: str) -> set[str]:
    """Tokenize after removing boilerplate and the explicit answer-key link."""
    cleaned = html.unescape(text or "")
    cleaned = _ANSWER_KEY.sub(" ", cleaned)
    cleaned = _BOILERPLATE.sub(" ", cleaned)
    return {
        token
        for token in _TOKEN.findall(cleaned.upper())
        if len(token) >= 3 and token not in _STOPWORDS
    }


def text_overlap_features(new_record: dict, prior_record: dict) -> dict:
    newer = meaningful_tokens(new_record.get("text", ""))
    older = meaningful_tokens(prior_record.get("text", ""))
    shared = newer & older
    union = newer | older
    containment = len(shared) / len(older) if older else 0.0
    jaccard = len(shared) / len(union) if union else 0.0
    same_part = bool(normalize_value(new_record.get("part_name"))) and (
        normalize_value(new_record.get("part_name"))
        == normalize_value(prior_record.get("part_name"))
    )
    same_jasc = bool(normalize_value(new_record.get("jasc_code"))) and (
        normalize_value(new_record.get("jasc_code"))
        == normalize_value(prior_record.get("jasc_code"))
    )
    same_location = bool(normalize_value(new_record.get("part_location"))) and (
        normalize_value(new_record.get("part_location"))
        == normalize_value(prior_record.get("part_location"))
    )
    # Equality bonuses are deliberately small: prose overlap is the primary
    # signal, while sparse structured fields can rescue terse true pairs.
    screen_score = min(
        1.0,
        max(containment, jaccard)
        + (SCREEN_WEIGHTS["part_name"] if same_part else 0.0)
        + (SCREEN_WEIGHTS["jasc_code"] if same_jasc else 0.0)
        + (SCREEN_WEIGHTS["part_location"] if same_location else 0.0),
    )
    return {
        "containment": containment,
        "jaccard": jaccard,
        "same_part_name": same_part,
        "same_jasc_code": same_jasc,
        "same_part_location": same_location,
        "shared_tokens": len(shared),
        "screen_score": screen_score,
    }
