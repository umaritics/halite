"""Helpers for presenting conflict-analysis state without mutating stored data."""

ANALYSIS_METADATA = (
    "analysis_state",
    "scored_at",
    "classification_label",
    "classification_rationale",
    "candidate_count",
    "candidates_considered",
    "analysis_model",
    "analysis_method",
    "analysed_at",
)


def is_legacy_placeholder(record: dict) -> bool:
    """Identify the old ingest default that looked like a real perfect score."""
    return (
        record.get("confidence") == 1.0
        and record.get("legacy_confidence") is None
        and not any(record.get(key) is not None for key in ANALYSIS_METADATA)
    )


def normalize_analysis_for_api(record: dict) -> dict:
    """Return an API view that exposes an untouched legacy score as unanalysed."""
    result = dict(record)
    if is_legacy_placeholder(result):
        result.update(
            confidence=None,
            analysis_state="unscored",
            legacy_placeholder=True,
        )
    return result
