"""Safety tests for the conflict-score backfill command."""

import sys

import pytest

from scripts import backfill_conflict_scores


class _DeadGroq:
    is_live = False


def test_backfill_refuses_to_run_without_live_groq(monkeypatch):
    """A staging backfill must never persist cache/stub classifications."""
    monkeypatch.setattr(backfill_conflict_scores, "Neo4jClient", lambda *_: object())
    monkeypatch.setattr(backfill_conflict_scores, "GraphRepository", lambda _: object())
    monkeypatch.setattr(backfill_conflict_scores, "GroqService", lambda **_: _DeadGroq())
    monkeypatch.setattr(sys, "argv", ["backfill_conflict_scores.py"])

    with pytest.raises(SystemExit) as exc_info:
        backfill_conflict_scores.main()

    assert exc_info.value.code == 1


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"analysis_state": "unscored", "confidence": None}, True),
        ({"analysis_state": "scored", "confidence": 1.0}, False),
        ({"analysis_state": "needs_review", "confidence": 0.4}, False),
        ({"analysis_state": "reviewed", "confidence": 0.8}, False),
        ({"confidence": 1.0}, True),
    ],
)
def test_resume_uses_analysis_state_only(record, expected):
    assert backfill_conflict_scores._is_unscored_placeholder(record) is expected
