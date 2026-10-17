import json
from datetime import datetime, timezone

import pytest

from domains.maintenance import MaintenanceDomainAdapter
from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from services.analysis_budget import BudgetExhausted, DailyBudgetManager
from services.conflict_engine import (
    classify_conflict,
    find_candidate_pairs,
    process_record,
    score_confidence,
)
from services.conflict_screen import meaningful_tokens


class SequenceGroq:
    is_live = True
    model = "test/cascade"

    def __init__(self, labels):
        self.labels = iter(labels)
        self.calls = 0

    def extract_json_with_usage(self, **_):
        self.calls += 1
        label = next(self.labels)
        return {
            "content": json.dumps({"label": label, "rationale": label}),
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "reasoning_tokens": 5,
                "total_tokens": 120,
            },
        }


def _repo_with(records):
    repo = GraphRepository(MemoryGraphStore())
    asset = repo.find_or_create_asset("NCASCADE", {})
    for record in records:
        repo.create_service_record({"asset_key": "NCASCADE", "source": "faa_sdr", **record})
        repo.link_record_about_asset(record["record_id"], asset["id"])
    return repo


def test_answer_key_is_removed_from_screen_and_date_is_not_a_feature():
    tokens = meaningful_tokens("SUPPLEMENTAL REPORT FOR (SWIA202512345678): pump seal cracked")
    assert "SUPPLEMENTAL" not in tokens
    assert "SWIA202512345678" not in tokens
    assert tokens == {"PUMP", "SEAL", "CRACKED"}


def test_containment_first_ranks_true_full_text_above_recent_sparse_match():
    repo = _repo_with([
        {"record_id": "FULL", "occurred_at": "2025-01-01", "part_name": "PUMP", "text": "hydraulic pump seal cracked leaking fluid"},
        {"record_id": "RECENT", "occurred_at": "2025-01-09", "part_name": "PUMP", "text": "routine pump inspection"},
        {"record_id": "NEW", "occurred_at": "2025-01-10", "part_name": "PUMP", "text": "hydraulic pump seal cracked leaking fluid replaced"},
    ])
    ranked = find_candidate_pairs(repo, "NEW", analysis_mode="cascade")
    assert ranked[0]["record"]["record_id"] == "FULL"
    assert ranked[0]["screen_features"]["containment"] == 1.0


def test_cascade_stops_after_two_agreeing_votes_and_meters_each_vote():
    groq = SequenceGroq(["supersedes", "supersedes"])
    result = classify_conflict(groq, {"record_id": "N", "text": "new"}, {"record_id": "P", "text": "prior"}, analysis_mode="cascade")
    assert groq.calls == 2
    assert result["method"] == "llm"
    assert result["passes"] == 2
    assert result["vote_agreement"] == 1.0
    assert result["prompt_tokens"] == 200
    assert result["total_tokens"] == 240
    assert len(result["votes"]) == 2


def test_cascade_escalates_disagreement_and_persistent_split_routes_review():
    labels = ["supersedes", "no_conflict", "supersedes", "no_conflict", "scope_disjoint"]
    groq = SequenceGroq(labels)
    repo = _repo_with([
        {"record_id": "P", "occurred_at": "2025-01-01", "part_name": "PUMP", "text": "hydraulic pump seal cracked"},
        {"record_id": "N", "occurred_at": "2025-01-02", "part_name": "PUMP", "text": "hydraulic pump seal cracked replaced"},
    ])
    processed = process_record(repo, groq, MaintenanceDomainAdapter(), "N", analysis_mode="cascade")
    result = processed["classification"]
    assert groq.calls == 5
    assert result["method"] == "llm-escalated"
    assert result["passes"] == 5
    assert result["vote_agreement"] == pytest.approx(0.4)
    assert result["vote_split"] is True
    assert processed["status_applied"] == "needs_review"


def test_cascade_screen_skips_model_and_persists_method_metadata():
    repo = _repo_with([
        {"record_id": "P", "occurred_at": "2025-01-01", "part_name": "PUMP", "text": "seal leak"},
        {"record_id": "N", "occurred_at": "2025-01-02", "part_name": "PUMP", "text": "unrelated inspection"},
    ])
    groq = SequenceGroq([])
    result = process_record(repo, groq, MaintenanceDomainAdapter(), "N", analysis_mode="cascade")
    stored = repo.get_service_record("N")
    assert groq.calls == 0
    assert result["analysis_method"] == "screen"
    assert stored["analysis_method"] == "screen"
    assert stored["analysis_passes"] == 0
    assert stored["analysis_total_tokens"] == 0
    assert stored["analysis_votes_json"] == "[]"


def test_positive_above_screen_threshold_is_retained_for_model():
    repo = _repo_with([
        {"record_id": "P", "occurred_at": "2025-01-01", "part_name": "PUMP", "jasc_code": "2913", "text": "hydraulic pump seal cracked leaking fluid"},
        {"record_id": "N", "occurred_at": "2025-01-02", "part_name": "PUMP", "jasc_code": "2913", "text": "hydraulic pump seal cracked leaking fluid replaced"},
    ])
    groq = SequenceGroq(["no_conflict", "no_conflict"])
    result = process_record(repo, groq, MaintenanceDomainAdapter(), "N", analysis_mode="cascade")
    assert groq.calls == 2
    assert result["analysis_method"] == "llm"


def test_legacy_mode_preserves_five_pass_golden_output(monkeypatch):
    monkeypatch.setenv("MAINT_SELF_CONSISTENCY_PASSES", "5")
    repo = _repo_with([
        {"record_id": "P", "occurred_at": "2025-01-01", "part_name": "PUMP", "jasc_code": "2913", "text": "pump seal cracked"},
        {"record_id": "N", "occurred_at": "2025-01-02", "part_name": "PUMP", "jasc_code": "2913", "text": "SUPPLEMENTAL REPORT FOR (P): pump replaced"},
    ])
    groq = SequenceGroq(["supersedes"] * 5)
    result = process_record(repo, groq, MaintenanceDomainAdapter(), "N", analysis_mode="legacy")
    assert groq.calls == 5
    assert result["classification"]["passes"] == 5
    assert result["classification"]["method"] == "llm"
    assert result["confidence"] == 1.0
    assert result["status_applied"] == "auto_accepted"


def test_vote_agreement_changes_cascade_confidence_without_using_pass_count():
    signals = {"classification_supersedes": True, "classification_vote_agreement": 0.6}
    assert score_confidence(signals) == pytest.approx(0.21)
    signals["classification_vote_agreement"] = 1.0
    assert score_confidence(signals) == pytest.approx(0.35)


def test_daily_budget_persists_and_rolls_over_at_utc_midnight(tmp_path):
    current = [datetime(2026, 10, 17, 23, 59, tzinfo=timezone.utc)]
    budget = DailyBudgetManager(
        tmp_path / "budget.json", request_limit=10, token_limit=1000,
        utilization=0.9, token_reserve=100, now_fn=lambda: current[0],
    )
    for _ in range(9):
        budget.before_request("model")
        budget.record_request("model", {"total_tokens": 50})
    with pytest.raises(BudgetExhausted, match="daily_request_budget"):
        budget.before_request("model")
    reloaded = DailyBudgetManager(
        tmp_path / "budget.json", request_limit=10, token_limit=1000,
        utilization=0.9, token_reserve=100, now_fn=lambda: current[0],
    )
    assert reloaded.snapshot("model")["requests_used"] == 9
    current[0] = datetime(2026, 10, 18, 0, 1, tzinfo=timezone.utc)
    assert reloaded.snapshot("model")["requests_used"] == 0


def test_daily_budget_stops_before_token_reserve_would_cross_cap(tmp_path):
    budget = DailyBudgetManager(
        tmp_path / "budget.json", request_limit=100, token_limit=1000,
        utilization=0.9, token_reserve=200,
    )
    budget.record_request("model", {"total_tokens": 750})
    with pytest.raises(BudgetExhausted, match="daily_token_budget"):
        budget.before_request("model")


def test_cached_classification_is_backward_compatible_and_does_not_bill(monkeypatch, tmp_path):
    from config import settings

    monkeypatch.setattr(settings, "MAINT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    old_entry = {"label": "no_conflict", "rationale": "legacy", "parse_failed": False}
    (tmp_path / "cache.json").write_text(
        json.dumps({"N_P_test/cascade": old_entry}), encoding="utf-8"
    )
    budget = DailyBudgetManager(
        tmp_path / "budget.json", request_limit=10, token_limit=1000,
        utilization=0.9, token_reserve=100,
    )
    groq = SequenceGroq([])
    result = classify_conflict(
        groq, {"record_id": "N", "text": "new"},
        {"record_id": "P", "text": "prior"},
        analysis_mode="cascade", budget_manager=budget,
    )
    assert result["cache_hit"] is True
    assert result["method"] == "llm"
    assert result["votes"] == []
    assert groq.calls == 0
    assert budget.snapshot(groq.model)["requests_used"] == 0
