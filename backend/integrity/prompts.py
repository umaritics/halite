"""System prompts for classifying a pair of records.

"v1" is the prompt staging uses and must stay byte for byte as it was. "v2-unannounced"
is a draft for the benchmark only: its definition of "supersedes" no longer asks for an
explicit update, because a report that corrects another without saying so never gives one.
Staging keeps v1 until Shahmeer decides otherwise.
"""
from __future__ import annotations

PROMPT_VERSION = "v1"

_V1 = """You are a technical conflict classifier for aviation maintenance records.

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

_V2_SUPERSEDES = (
    "  supersedes           — new record reports the same event as the prior record and completes "
    "or corrects it (for example it names the failed part, the cause or the corrective action), "
    "so the prior record is out of date"
)
_V2_PARTIAL = (
    "  partial_supersedes   — new record reports the same event as the prior record and corrects "
    "only part of it, so both records are still needed"
)

_V2 = (
    _V1
    .replace(
        "  supersedes           — new record explicitly updates or closes the prior record",
        _V2_SUPERSEDES,
    )
    .replace(
        "  partial_supersedes   — new record addresses the same issue but only partially resolves it",
        _V2_PARTIAL,
    )
)

CLASSIFICATION_PROMPTS: dict[str, str] = {"v1": _V1, "v2-unannounced": _V2}


def system_prompt(version: str = PROMPT_VERSION) -> str:
    try:
        return CLASSIFICATION_PROMPTS[version]
    except KeyError:
        raise ValueError(
            f"unknown prompt version {version!r}; expected one of {sorted(CLASSIFICATION_PROMPTS)}"
        ) from None
