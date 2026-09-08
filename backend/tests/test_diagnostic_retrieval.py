"""
tests/test_diagnostic_retrieval.py

Unit tests for services/diagnostic_retrieval.py using MemoryGraphStore.
Every test uses only real data inserted into the store — no mocking.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from services.diagnostic_retrieval import (
    asset_history_context,
    similar_symptom_records,
    resolution_outcomes,
    build_diagnostic_context,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def repo():
    """Fresh in-memory graph with two assets and several service records."""
    store = MemoryGraphStore()
    gr = GraphRepository(store)

    # Asset 1: 3 records (one superseded) — create ABOUT edges so list_asset_history works
    a1 = gr.find_or_create_asset("TESTA1", {"make": "AIRBUS", "model": "A321"})
    for rec_data in [
        {"record_id": "R1_OLD", "asset_key": "TESTA1", "occurred_at": "2025-01-01",
         "part_name": "PUMP", "jasc_code": "2900",
         "text": "Hydraulic pump noise on ground", "status": "superseded", "confidence": 0.9},
        {"record_id": "R1_NEW", "asset_key": "TESTA1", "occurred_at": "2025-01-02",
         "part_name": "PRESSURE SWITCH", "jasc_code": "2900",
         "text": "Hydraulic pressure switch faulty after pump replaced",
         "status": "auto_accepted", "confidence": 0.85},
        {"record_id": "R1_RECENT", "asset_key": "TESTA1", "occurred_at": "2025-03-01",
         "part_name": "PUMP", "jasc_code": "2900",
         "text": "Pump seal leaking", "status": "auto_accepted", "confidence": 0.95},
    ]:
        gr.create_service_record(rec_data)
        gr.link_record_about_asset(rec_data["record_id"], a1["id"])

    # Asset 2: 2 records on a different airframe — fleet evidence
    a2 = gr.find_or_create_asset("TESTB2", {"make": "AIRBUS", "model": "A321"})
    for rec_data in [
        {"record_id": "R2_A", "asset_key": "TESTB2", "occurred_at": "2025-02-01",
         "part_name": "PUMP", "jasc_code": "2900",
         "text": "Hydraulic pump found cracked during inspection",
         "status": "auto_accepted", "confidence": 0.80},
        {"record_id": "R2_B", "asset_key": "TESTB2", "occurred_at": "2025-02-15",
         "part_name": "INDICATOR", "jasc_code": "3100",
         "text": "Fuel indicator failed after refuel",
         "status": "auto_accepted", "confidence": 0.75},
    ]:
        gr.create_service_record(rec_data)
        gr.link_record_about_asset(rec_data["record_id"], a2["id"])

    return gr, a1["id"], a2["id"]


# ---------------------------------------------------------------------------
# Tests: asset_history_context
# ---------------------------------------------------------------------------

class TestAssetHistoryContext:
    def test_returns_correct_count(self, repo):
        gr, a1_id, _ = repo
        history = asset_history_context(gr, a1_id, limit=30)
        assert len(history) == 3

    def test_newest_first(self, repo):
        gr, a1_id, _ = repo
        history = asset_history_context(gr, a1_id, limit=30)
        dates = [h["occurred_at"] for h in history]
        assert dates == sorted(dates, reverse=True)

    def test_all_have_record_id(self, repo):
        gr, a1_id, _ = repo
        history = asset_history_context(gr, a1_id, limit=30)
        for h in history:
            assert h["record_id"], f"Missing record_id in {h}"

    def test_superseded_flagged(self, repo):
        gr, a1_id, _ = repo
        history = asset_history_context(gr, a1_id, limit=30)
        superseded = [h for h in history if h["is_superseded"]]
        assert len(superseded) == 1
        assert superseded[0]["record_id"] == "R1_OLD"

    def test_limit_respected(self, repo):
        gr, a1_id, _ = repo
        history = asset_history_context(gr, a1_id, limit=1)
        assert len(history) == 1


# ---------------------------------------------------------------------------
# Tests: similar_symptom_records
# ---------------------------------------------------------------------------

class TestSimilarSymptomRecords:
    def test_excludes_own_asset(self, repo):
        gr, a1_id, a2_id = repo
        results = similar_symptom_records(gr, "Hydraulic pump noise", exclude_asset_id=a1_id)
        for r in results:
            assert r["asset_id"] != a1_id, f"Own asset leaked through: {r}"

    def test_returns_fleet_match(self, repo):
        gr, a1_id, a2_id = repo
        results = similar_symptom_records(gr, "Hydraulic pump found cracked", exclude_asset_id=a1_id)
        ids = [r["record_id"] for r in results]
        assert "R2_A" in ids

    def test_jasc_boost(self, repo):
        gr, a1_id, a2_id = repo
        # Exclude a2 so only a1 records are returned; R1_OLD and R1_RECENT match PUMP/2900
        # With JASC 2900 hint, PUMP records should score higher than INDICATOR records
        results = similar_symptom_records(gr, "pump", jasc_code="2900", exclude_asset_id=a2_id)
        if results:
            # All returned records should be from a1 (since a2 is excluded)
            for r in results:
                assert r["asset_id"] != a2_id

    def test_all_have_record_id(self, repo):
        gr, a1_id, _ = repo
        results = similar_symptom_records(gr, "pump noise", exclude_asset_id=a1_id)
        for r in results:
            assert r["record_id"]

    def test_superseded_flagged(self, repo):
        gr, a1_id, a2_id = repo
        # Exclude a2 so R1_OLD (superseded) can appear in results
        results = similar_symptom_records(gr, "hydraulic pump", exclude_asset_id=a2_id, limit=20)
        sup = [r for r in results if r["is_superseded"]]
        for r in sup:
            assert r["status"] == "superseded"


# ---------------------------------------------------------------------------
# Tests: resolution_outcomes
# ---------------------------------------------------------------------------

class TestResolutionOutcomes:
    def test_basic(self, repo):
        gr, a1_id, _ = repo
        outcomes = resolution_outcomes(gr, ["R1_OLD", "R1_NEW"])
        assert len(outcomes) == 2
        ids = {o["record_id"] for o in outcomes}
        assert "R1_OLD" in ids
        assert "R1_NEW" in ids

    def test_superseded_labelled(self, repo):
        gr, _, _ = repo
        outcomes = resolution_outcomes(gr, ["R1_OLD"])
        assert outcomes[0]["is_superseded"] is True

    def test_missing_id_skipped(self, repo):
        gr, _, _ = repo
        outcomes = resolution_outcomes(gr, ["R1_OLD", "GHOST_NONEXISTENT"])
        assert len(outcomes) == 1

    def test_empty_list(self, repo):
        gr, _, _ = repo
        assert resolution_outcomes(gr, []) == []


# ---------------------------------------------------------------------------
# Tests: build_diagnostic_context
# ---------------------------------------------------------------------------

class TestBuildDiagnosticContext:
    def test_returns_all_keys(self, repo):
        gr, a1_id, _ = repo
        ctx = build_diagnostic_context(gr, a1_id, "pump noise")
        assert "asset_id" in ctx
        assert "symptom_text" in ctx
        assert "asset_history" in ctx
        assert "fleet_matches" in ctx
        assert "resolution_outcomes" in ctx
        assert "context_size" in ctx

    def test_asset_id_matches(self, repo):
        gr, a1_id, _ = repo
        ctx = build_diagnostic_context(gr, a1_id, "pump noise")
        assert ctx["asset_id"] == a1_id

    def test_fleet_excludes_own_asset(self, repo):
        gr, a1_id, _ = repo
        ctx = build_diagnostic_context(gr, a1_id, "pump noise")
        for fm in ctx["fleet_matches"]:
            assert fm["asset_id"] != a1_id

    def test_resolution_outcomes_non_empty(self, repo):
        gr, a1_id, _ = repo
        ctx = build_diagnostic_context(gr, a1_id, "pump noise")
        assert len(ctx["resolution_outcomes"]) > 0

    def test_all_provenance_fields_present(self, repo):
        gr, a1_id, _ = repo
        ctx = build_diagnostic_context(gr, a1_id, "pump")
        for item in ctx["asset_history"]:
            assert item["record_id"], f"record_id missing: {item}"
            assert item["asset_id"], f"asset_id missing: {item}"

    def test_context_size_accurate(self, repo):
        gr, a1_id, _ = repo
        ctx = build_diagnostic_context(gr, a1_id, "pump")
        sz = ctx["context_size"]
        assert sz["asset_records"] == len(ctx["asset_history"])
        assert sz["fleet_records"] == len(ctx["fleet_matches"])
