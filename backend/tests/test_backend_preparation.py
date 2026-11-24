"""Integration contracts for vertical registration and compatibility imports."""
import pytest
from fastapi.testclient import TestClient

from config import Settings
from tests.conftest import _build_test_app


SUMMARIES = [
    ("retrieval", "Retrieval and ranking", "/app/search"),
    ("evaluation", "Retrieval evaluation", "/app/evaluation"),
    ("integrity", "Record integrity", "/app/integrity"),
    ("sessions", "Investigation sessions", "/app/investigations"),
]


@pytest.mark.parametrize("vertical,title,link", SUMMARIES)
def test_summary_contract_and_single_registration(client, vertical, title, link):
    path = f"/api/{vertical}/summary"
    response = client.get(path)
    assert response.status_code == 200
    assert response.json() == {"title": title, "link": link, "stats": []}
    routes = [r for r in client.app.routes if getattr(r, "path", None) == path]
    assert len(routes) == 1
    assert routes[0].methods == {"GET"}


@pytest.mark.parametrize("vertical,title,link", SUMMARIES)
def test_summary_inherits_production_authentication(vertical, title, link):
    settings = Settings(
        DEMO_MODE=False, DATABASE_URL="sqlite+pysqlite:///:memory:",
        HALITE_API_KEY="phase1-test-only-key", RATE_LIMIT_ENABLED=False,
    )
    with TestClient(_build_test_app(settings_override=settings)) as client:
        path = f"/api/{vertical}/summary"
        assert client.get(path).status_code == 401
        response = client.get(path, headers={"X-Halite-Api-Key": settings.HALITE_API_KEY})
        assert response.status_code == 200
        assert response.json()["stats"] == []


def test_compatibility_imports_keep_the_same_classes():
    from graph.queries import GraphRepository
    from graph.repo import GraphRepository as NewRepository
    from graph.memory_store import MemoryGraphStore
    from graph.memory import MemoryGraphStore as NewMemory
    from db.models import Base, User
    from db.models.identity import Base as IdentityBase, User as IdentityUser
    assert GraphRepository is NewRepository
    assert MemoryGraphStore is NewMemory
    assert Base is IdentityBase
    assert User is IdentityUser
    assert set(Base.metadata.tables) == {
        "organizations", "users", "user_sessions", "user_invites", "audit_events",
        "diagnostic_sessions", "session_turns", "session_snapshots", "review_decisions",
    }


def test_split_preserves_cross_mixin_calls_and_ingest_idempotency():
    from graph.repo import GraphRepository
    from graph.memory import MemoryGraphStore
    repo = GraphRepository(MemoryGraphStore())
    asset = repo.find_or_create_asset("PHASE1", {"model": "TEST"})
    for record_id, date in [("OLD", "2024-01-01"), ("NEW", "2024-01-02")]:
        data = {"record_id": record_id, "asset_key": "PHASE1", "occurred_at": date}
        first = repo.create_service_record(data)
        assert repo.create_service_record(data)["id"] == first["id"]
        repo.link_record_about_asset(record_id, asset["id"])
        repo.link_record_about_asset(record_id, asset["id"])
    repo.link_record_supersedes("NEW", "OLD", "supersedes", .9, "test")
    assert repo.count_service_records() == 2
    assert repo.list_assets_with_counts()[0]["record_count"] == 2
    assert repo.list_asset_history_recent(asset["id"])[0]["record_id"] == "NEW"
    assert repo.list_corrections_page()["total"] == 1
    repo.update_service_record("NEW", {"analysis_state": "reviewed"})
    assert repo.analysis_status()["reviewed"] == 1
    assert len(repo.graph_overview()["nodes"]) == 3
