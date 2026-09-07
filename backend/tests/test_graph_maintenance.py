"""
test_graph_maintenance.py — Parameterised tests for maintenance-domain graph operations.

Tests are parameterised over MemoryGraphStore (always runs) and Neo4jClient
(SKIPS with an explicit reason if Neo4j is unreachable — never silently passes).

Coverage:
  - find_or_create_asset: creates new, returns existing on repeat call
  - create_service_record: idempotent on record_id
  - get_service_record: returns correct record
  - link_record_about_asset: ABOUT edge stored correctly
  - list_asset_history: ascending by occurred_at, respects limit
  - link_record_supersedes: SUPERSEDES edge created
  - list_service_records: filters by status, by asset_id
  - update_service_record: partial update reflected
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Store parametrisation helpers
# ---------------------------------------------------------------------------

def _memory_repo():
    from graph.memory_store import MemoryGraphStore
    from graph.queries import GraphRepository
    return GraphRepository(MemoryGraphStore())


def _neo4j_repo_or_skip():
    """Return a Neo4j-backed GraphRepository, or skip the test if unreachable."""
    from graph.neo4j_client import Neo4jClient
    from graph.queries import GraphRepository
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "localdevpassword")

    if not (uri and password):
        pytest.skip("NEO4J_URI / NEO4J_PASSWORD not set — Neo4j test skipped")

    try:
        client = Neo4jClient(uri, user, password, database="neo4j")
        client.init_schema()
        return GraphRepository(client)
    except Exception as exc:
        pytest.skip(f"Neo4j unreachable ({exc}) — Neo4j test skipped")


@pytest.fixture(params=["memory", "neo4j"])
def repo(request):
    if request.param == "memory":
        r = _memory_repo()
        yield r
    else:
        r = _neo4j_repo_or_skip()
        yield r
        # Cleanup: remove any ServiceRecord / Asset nodes created during this test
        try:
            r.store.run_query(
                "MATCH (n) WHERE n:ServiceRecord OR n:Asset DETACH DELETE n"
            )
            r.store.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFindOrCreateAsset:
    def test_creates_new_asset(self, repo):
        asset = repo.find_or_create_asset("N12345", {"make": "Boeing", "model": "737"})
        assert asset["tail_number"] == "N12345"
        assert asset["make"] == "Boeing"
        assert "id" in asset

    def test_returns_existing_on_repeat(self, repo):
        a1 = repo.find_or_create_asset("N99999", {"make": "Airbus"})
        a2 = repo.find_or_create_asset("N99999", {"make": "Airbus"})
        assert a1["id"] == a2["id"], "Should return same node on second call"

    def test_different_tails_are_different_assets(self, repo):
        a1 = repo.find_or_create_asset("NTAIL1", {})
        a2 = repo.find_or_create_asset("NTAIL2", {})
        assert a1["id"] != a2["id"]


class TestCreateServiceRecord:
    def test_creates_record(self, repo):
        sr = repo.create_service_record({
            "record_id": "TEST001",
            "asset_key": "N12345",
            "occurred_at": "2025-01-15",
            "text": "Emergency exit sign missing.",
            "part_name": "Exit Sign",
        })
        assert sr["record_id"] == "TEST001"
        assert sr["text"] == "Emergency exit sign missing."
        assert sr["status"] == "auto_accepted"  # default

    def test_idempotent_on_record_id(self, repo):
        data = {"record_id": "IDEMP001", "asset_key": "NTEST", "occurred_at": "2025-01-01", "text": "x"}
        sr1 = repo.create_service_record(data)
        sr2 = repo.create_service_record(data)
        assert sr1["id"] == sr2["id"], "Should return same node on second call"

    def test_custom_status(self, repo):
        sr = repo.create_service_record({
            "record_id": "STAT001",
            "asset_key": "N00000",
            "occurred_at": "2025-02-01",
            "text": "test",
            "status": "needs_review",
            "confidence": 0.5,
        })
        assert sr["status"] == "needs_review"
        assert sr["confidence"] == 0.5


class TestGetServiceRecord:
    def test_returns_record(self, repo):
        repo.create_service_record({
            "record_id": "GET001",
            "asset_key": "NGET",
            "occurred_at": "2025-03-01",
            "text": "test get",
        })
        result = repo.get_service_record("GET001")
        assert result is not None
        assert result["record_id"] == "GET001"

    def test_returns_none_for_unknown(self, repo):
        result = repo.get_service_record("NONEXISTENT_99999")
        assert result is None


class TestLinkRecordAboutAsset:
    def test_link_creates_retrievable_history(self, repo):
        asset = repo.find_or_create_asset("NLINK01", {})
        sr = repo.create_service_record({
            "record_id": "LINK001",
            "asset_key": "NLINK01",
            "occurred_at": "2025-04-01",
            "text": "linked record",
        })
        repo.link_record_about_asset("LINK001", asset["id"])
        history = repo.list_asset_history(asset["id"])
        assert len(history) == 1
        assert history[0]["record_id"] == "LINK001"


class TestListAssetHistory:
    def test_ascending_order(self, repo):
        asset = repo.find_or_create_asset("NHIST01", {})
        for i, date in enumerate(["2025-03-01", "2025-01-01", "2025-02-01"]):
            repo.create_service_record({
                "record_id": f"HIST{i:03d}",
                "asset_key": "NHIST01",
                "occurred_at": date,
                "text": f"record {i}",
            })
            repo.link_record_about_asset(f"HIST{i:03d}", asset["id"])

        history = repo.list_asset_history(asset["id"])
        occurred = [r["occurred_at"] for r in history]
        assert occurred == sorted(occurred), f"Expected ascending order: {occurred}"

    def test_limit_respected(self, repo):
        asset = repo.find_or_create_asset("NHIST02", {})
        for i in range(5):
            repo.create_service_record({
                "record_id": f"LIM{i:03d}",
                "asset_key": "NHIST02",
                "occurred_at": f"2025-0{i+1}-01",
                "text": f"r{i}",
            })
            repo.link_record_about_asset(f"LIM{i:03d}", asset["id"])

        limited = repo.list_asset_history(asset["id"], limit=2)
        assert len(limited) == 2


class TestLinkRecordSupersedes:
    def test_supersedes_edge_created(self, repo):
        repo.create_service_record({
            "record_id": "OLD001", "asset_key": "NSUP", "occurred_at": "2025-01-01", "text": "old"
        })
        repo.create_service_record({
            "record_id": "NEW001", "asset_key": "NSUP", "occurred_at": "2025-01-02", "text": "new"
        })
        # Should not raise
        repo.link_record_supersedes("NEW001", "OLD001", "full", 0.9, "Direct FAA citation")

        # Verify by checking that a SUPERSEDES edge can be looked up via the store
        if repo.is_memory:
            new_nodes = repo.store._find_nodes("ServiceRecord", record_id="NEW001")
            assert new_nodes, "NEW001 should exist"
            edges = [e for e in repo.store.edges if e["type"] == "SUPERSEDES"]
            assert len(edges) == 1
            assert edges[0]["properties"]["confidence"] == 0.9


class TestListServiceRecords:
    def test_filter_by_status(self, repo):
        repo.create_service_record({
            "record_id": "LS001", "asset_key": "NLS", "occurred_at": "2025-01-01",
            "text": "r1", "status": "needs_review",
        })
        repo.create_service_record({
            "record_id": "LS002", "asset_key": "NLS", "occurred_at": "2025-01-02",
            "text": "r2", "status": "auto_accepted",
        })
        needs_review = repo.list_service_records(status="needs_review")
        record_ids = [r["record_id"] for r in needs_review]
        assert "LS001" in record_ids
        assert "LS002" not in record_ids

    def test_filter_by_asset(self, repo):
        a1 = repo.find_or_create_asset("NFILT1", {})
        a2 = repo.find_or_create_asset("NFILT2", {})
        repo.create_service_record({
            "record_id": "FA001", "asset_key": "NFILT1", "occurred_at": "2025-01-01", "text": "a1 rec"
        })
        repo.link_record_about_asset("FA001", a1["id"])
        repo.create_service_record({
            "record_id": "FA002", "asset_key": "NFILT2", "occurred_at": "2025-01-02", "text": "a2 rec"
        })
        repo.link_record_about_asset("FA002", a2["id"])

        records_a1 = repo.list_service_records(asset_id=a1["id"])
        record_ids = [r["record_id"] for r in records_a1]
        assert "FA001" in record_ids
        assert "FA002" not in record_ids


class TestUpdateServiceRecord:
    def test_partial_update(self, repo):
        repo.create_service_record({
            "record_id": "UPD001", "asset_key": "NUPD", "occurred_at": "2025-01-01",
            "text": "before", "status": "needs_review",
        })
        updated = repo.update_service_record("UPD001", {"status": "accepted", "confidence": 0.95})
        assert updated is not None
        assert updated["status"] == "accepted"
        assert updated["confidence"] == 0.95
        # text should still be there
        assert updated.get("text") == "before"

    def test_update_nonexistent_returns_none(self, repo):
        result = repo.update_service_record("GHOST9999", {"status": "accepted"})
        assert result is None
