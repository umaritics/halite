"""Hide the announcement of a correction, so the benchmark measures the unannounced case.

M1 removes the citation. M2 also removes the other formatting that gives away how far a report is
along its life (the "will be submitted" sentence and the OPEN and CLOSED markers). Masking is applied
to every text the model can see, prior as well as new, because a prior can itself be a supplemental report.
"""
from __future__ import annotations

import re

from integrity.citations import CITATION_RE, OPEN_MARKER_RE, parse_citations

MASKINGS = ("M1", "M2")

_CITATION_WITH_COLON = re.compile(CITATION_RE.pattern + r"\s*:?", re.IGNORECASE)
# FAA writes the sentence as **SUPPLEMENTAL REPORT WILL BE SUBMITTED.** with stray spaces and asterisks.
_OPEN_SENTENCE = re.compile(
    r"(?:\*+\s*)?" + OPEN_MARKER_RE.pattern + r"(?:\s*\.)?(?:\s*\*+)?", re.IGNORECASE
)
_STATUS_MARKER = re.compile(r"(?:\*+\s*)?\(\s*(?:OPEN|CLOSED)\s*\)(?:\s*\*+)?", re.IGNORECASE)
_STATUS_MARKER_LEFT = re.compile(r"\(\s*(?:OPEN|CLOSED)\s*\)", re.IGNORECASE)


def _check(masking: str) -> None:
    if masking not in MASKINGS:
        raise ValueError(f"unknown masking {masking!r}; expected one of {MASKINGS}")


def _drop_real_citation(match: re.Match) -> str:
    # Same test as parse_citations: a token without a digit is an ordinary word, not an ID.
    return " " if any(ch.isdigit() for ch in match.group(1)) else match.group(0)


def _id_pattern(record_id: str) -> re.Pattern:
    escaped = re.escape(record_id)
    return re.compile(rf"\(\s*{escaped}\s*\)|(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


def mask_text(text: str, masking: str, extra_ids=()) -> str:
    """Return text without the announcement; extra_ids are the cited IDs that may also appear inline."""
    _check(masking)
    masked = _CITATION_WITH_COLON.sub(_drop_real_citation, text or "")
    for record_id in sorted(extra_ids):
        masked = _id_pattern(record_id).sub(" ", masked)
    if masking == "M2":
        masked = _OPEN_SENTENCE.sub(" ", masked)
        masked = _STATUS_MARKER.sub(" ", masked)
    return " ".join(masked.split())


def leaks(text: str, masking: str, extra_ids=()) -> list[str]:
    """Names of anything masking should have removed that is still in the text; empty means clean."""
    _check(masking)
    found = []
    if parse_citations(text):
        found.append("citation")
    if any(_id_pattern(record_id).search(text or "") for record_id in extra_ids):
        found.append("cited_id")
    if masking == "M2":
        if OPEN_MARKER_RE.search(text or ""):
            found.append("open_marker")
        if _STATUS_MARKER_LEFT.search(text or ""):
            found.append("status_marker")
    return found
