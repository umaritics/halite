"""Tests for backend/retrieval/service.py."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from retrieval.service import (
    normalize_mode,
    rank,
    rank_checks_from_context,
    ranker_version,
)
from services.diagnostic_retrieval import build_diagnostic_context, rank_diagnostic_checks


@pytest.fixture()
def graph_repo():
    store = MemoryGraphStore()
    gr = GraphRepository(store)
    asset = gr.find_or_create_asset("N123", {"make": "TEST", "model": "M1"})
    gr.create_service_record(
        {
            "record_id": "REC1",
            "asset_key": "N123",
            "occurred_at": "2025-01-01",
            "part_name": "PUMP",
            "text": "hydraulic leak",
            "status": "auto_accepted",
        }
    )
    gr.link_record_about_asset("REC1", asset["id"])
    return gr, asset["id"]


def test_normalize_mode_aliases():
    assert normalize_mode("b1") == "mid_heuristic"
    assert normalize_mode("b0") == "mid_fixed"
    assert normalize_mode("b5") == "hybrid_rrf"


def test_rank_checks_mid_fixed_differs_from_b1(graph_repo):
    gr, aid = graph_repo
    ctx = build_diagnostic_context(gr, aid, "hydraulic leak")
    b1 = rank_checks_from_context(ctx, "mid_heuristic")
    b0 = rank_checks_from_context(ctx, "mid_fixed")
    assert b1 and b0
    assert ranker_version("mid_fixed") != ranker_version("mid_heuristic")


def test_rank_mid_heuristic_matches_legacy_copilot(graph_repo):
    gr, _ = graph_repo
    state = {"symptoms": ["hydraulic leak"], "observations": [], "ruled_out": []}
    result = rank(gr, symptoms=state["symptoms"], mode="mid_heuristic")
    from services.diagnostic_retrieval import build_copilot_context, rank_copilot_checks

    ctx = build_copilot_context(gr, None, state)
    expected = rank_copilot_checks(ctx, [])[:10]
    assert result["hypotheses"] == expected
    assert result["mode"] == "mid_heuristic"


def test_offline_mode_falls_back_without_corpus(graph_repo, monkeypatch):
    gr, _ = graph_repo
    monkeypatch.setattr("retrieval.service._resolve_raw_dir", lambda: None)
    result = rank(gr, symptoms=["leak"], mode="dense")
    assert result["mode"] == "mid_heuristic"
    assert result["warnings"]