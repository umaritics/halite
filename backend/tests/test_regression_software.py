"""
test_regression_software.py — Regression suite for the existing software domain.

Every test here must stay GREEN through all subsequent tasks (T1-T10).
If any test turns red, the current task is blocked until it is fixed.

Coverage:
  - App boots and /health responds correctly
  - /api/decisions lists seeded decisions
  - /api/graph/overview returns nodes and edges
  - /api/ingest/document accepts a file and creates ≥1 decision
  - /api/alerts responds
  - invalidate_decisions_for_files flags a decision when a linked component's file changes
"""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# T0-R1  App boots and /health returns expected shape
# ---------------------------------------------------------------------------

def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok", f"status not 'ok': {data}"
    assert "app" in data, f"'app' key missing: {data}"
    assert "demo_mode" in data, f"'demo_mode' key missing: {data}"


def test_api_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# T0-R2  /api/decisions lists seeded decisions
# ---------------------------------------------------------------------------

def test_decisions_lists_seeded(client):
    resp = client.get("/api/decisions")
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    # Demo data seeds exactly 2 decisions: 'JWT over sessions', 'PostgreSQL over MongoDB'
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) >= 1, f"Expected ≥1 seeded decision, got: {data}"
    titles = {d.get("title", "") for d in data}
    assert any("JWT" in t or "PostgreSQL" in t for t in titles), (
        f"Expected seeded decisions, got titles: {titles}"
    )


# ---------------------------------------------------------------------------
# T0-R3  /api/graph/overview returns nodes and edges
# ---------------------------------------------------------------------------

def test_graph_overview_returns_structure(client):
    resp = client.get("/api/graph/overview")
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert "nodes" in data, f"'nodes' missing: {data.keys()}"
    assert "edges" in data, f"'edges' missing: {data.keys()}"
    assert len(data["nodes"]) >= 1, f"Expected ≥1 node from seeded data: {data}"


# ---------------------------------------------------------------------------
# T0-R4  /api/ingest/document accepts a file and creates ≥1 decision
# ---------------------------------------------------------------------------

def test_ingest_document_creates_decision(client):
    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "sample_meeting_transcript.txt",
    )
    assert os.path.exists(sample_path), f"Sample file not found: {sample_path}"

    with open(sample_path, "rb") as f:
        content = f.read()

    resp = client.post(
        "/api/ingest/document",
        files={"file": ("sample_meeting_transcript.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert "decisions_created" in data, f"'decisions_created' missing: {data}"
    assert data["decisions_created"] >= 1, (
        f"Expected ≥1 decision created from sample transcript, got: {data}"
    )


# ---------------------------------------------------------------------------
# T0-R5  /api/alerts responds (may be empty list)
# ---------------------------------------------------------------------------

def test_alerts_responds(client):
    resp = client.get("/api/alerts")
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert isinstance(data, list), f"Expected list: {data}"


# ---------------------------------------------------------------------------
# T0-R6  invalidate_decisions_for_files flags a linked decision
# ---------------------------------------------------------------------------

def test_invalidation_flags_linked_decision(graph_repo):
    """
    Steps:
    1. Verify seeded 'AuthModule' component exists at 'src/auth/auth.service.ts'
    2. Verify 'JWT over sessions' decision is linked to it (ABOUT)
    3. Create a fake Commit
    4. Call invalidate_decisions_for_files with that file path
    5. Assert the returned flagged list contains the JWT decision
    6. Assert its status is 'needs_review'
    """
    from graph.memory_store import MemoryGraphStore
    from graph.queries import GraphRepository

    # Use a fresh seeded store so we control the exact state
    store = MemoryGraphStore()
    store.seed_demo_data()
    repo = GraphRepository(store)

    # Confirm component exists
    comp = repo.find_component_by_path("src/auth/auth.service.ts")
    assert comp is not None, "AuthModule component not found at expected path"

    # Create a fake commit so the MAY_INVALIDATE edge can be created
    repo.create_commit({
        "id": "abc123test",
        "message": "Test commit touching auth",
        "author": "tester",
        "files_changed": ["src/auth/auth.service.ts"],
    })

    # Run invalidation
    flagged = repo.invalidate_decisions_for_files(
        "abc123test", ["src/auth/auth.service.ts"]
    )
    assert len(flagged) >= 1, f"Expected ≥1 flagged decision, got: {flagged}"

    flagged_titles = [f.get("title", "") for f in flagged]
    assert any("JWT" in t for t in flagged_titles), (
        f"Expected JWT decision to be flagged, got: {flagged_titles}"
    )

    # Verify status was updated in the graph
    decisions = repo.list_decisions(status="needs_review")
    jwt_decisions = [d for d in decisions if "JWT" in d.get("title", "")]
    assert len(jwt_decisions) >= 1, (
        f"JWT decision not in needs_review after invalidation. needs_review decisions: {decisions}"
    )
