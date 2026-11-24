"""Announced corrections: a report that names the report it corrects.

The patterns are identical to the ones in investigation/experiments/offline.py and
services/conflict_screen.py so the three verticals agree on what counts as a citation.
"""
from __future__ import annotations

import re

CITATION_RE = re.compile(r"SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*([A-Z0-9]{6,})\s*\)?", re.IGNORECASE)
OPEN_MARKER_RE = re.compile(r"SUPPLEMENTAL\s+REPORT\s+WILL\s+BE\s+SUBMITTED", re.IGNORECASE)


def parse_citations(text: str | None) -> list[str]:
    """Return each cited report ID once, upper-cased, in order of first appearance.

    The engine used to test only for the phrase and then guess the target; reading the
    ID is what lets a citation link to the report it actually names. A token without a digit
    is an ordinary word ("...FOR ENGINE FAILURE"), not a record ID, so it is not a citation.
    """
    if not text:
        return []
    seen: dict[str, None] = {}
    for match in CITATION_RE.finditer(text):
        token = match.group(1).upper()
        if any(ch.isdigit() for ch in token):
            seen.setdefault(token)
    return list(seen)


def has_open_marker(text: str | None) -> bool:
    """True when the report says a supplement is still to come (it corrects nothing yet)."""
    return bool(text) and OPEN_MARKER_RE.search(text) is not None
