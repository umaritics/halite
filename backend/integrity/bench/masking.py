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
# AA files resubmissions that name the original ("ORIGINAL REPORT WAS <id>"); the id is as good as a citation.
_ORIGINAL_REPORT = re.compile(r"ORIGINAL\s+REPORT\s+(?:WAS|FOR)\s*\(?\s*([A-Z0-9]{6,})\s*\)?\s*:?", re.IGNORECASE)
# The "supplemental report" phrase in every wording and misspelling seen in the FAA files, with the few
# filler words that follow it ("WILL BE SUBMITTED", "REQUIRED", "FOR SDR <id>"), so no half sentence is left.
_SUPPLEMENTAL_PHRASE = re.compile(
    r"SU\w*PLE\w*\s+REP\w*(?:\s+(?:FOR|TO|THE|ORIGINAL|WILL|WIL+|WAS|BE|REQUIRED|SDR|SUBMIT\w*|#?\d+"
    r"|\(?(?=[A-Z0-9]{6,})[A-Z0-9]*\d[A-Z0-9]*\)?))*\s*[:.]?",
    re.IGNORECASE,
)
# What a survivor looks like, deliberately wider than what the masks above match.
_SUPPLEMENTAL_SURVIVOR = re.compile(r"SU\w*PLE\w*\W+REP", re.IGNORECASE)
_STATUS_MARKER = re.compile(r"\(\s*(?:OPEN|CLOSED)\s*\)", re.IGNORECASE)
_EMPHASIS = re.compile(r"\*+")


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
    """Return text without the announcement; extra_ids are the cited IDs that may also appear inline.

    FAA wraps the announcement in bold marks (**), and only announced reports have them, so every
    asterisk run goes in both maskings; a leftover seam would tell the model the label.
    """
    _check(masking)
    masked = _CITATION_WITH_COLON.sub(_drop_real_citation, text or "")
    masked = _ORIGINAL_REPORT.sub(_drop_real_citation, masked)
    for record_id in sorted(extra_ids):
        masked = _id_pattern(record_id).sub(" ", masked)
    masked = _EMPHASIS.sub(" ", masked)
    if masking == "M2":
        masked = _SUPPLEMENTAL_PHRASE.sub(" ", masked)
        masked = _STATUS_MARKER.sub(" ", masked)
    return " ".join(masked.split())


def leaks(text: str, masking: str, extra_ids=()) -> list[str]:
    """Names of anything masking should have removed that is still in the text; empty means clean."""
    _check(masking)
    text = text or ""
    found = []
    if parse_citations(text) or any(_drop_real_citation(m) == " " for m in _ORIGINAL_REPORT.finditer(text)):
        found.append("citation")
    if any(_id_pattern(record_id).search(text) for record_id in extra_ids):
        found.append("cited_id")
    if "*" in text:
        found.append("emphasis_marks")
    if masking == "M2":
        if _SUPPLEMENTAL_SURVIVOR.search(text) or OPEN_MARKER_RE.search(text):
            found.append("open_marker")
        if _STATUS_MARKER.search(text):
            found.append("status_marker")
    return found
