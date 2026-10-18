"""DELETE /api/graph/reset is destructive: it needs the operations token (and, for Neo4j, confirm=WIPE)."""
from fastapi.testclient import TestClient

TOKEN = "test-ops-token"


def _node_count(client: TestClient) -> int:
    return len(client.app.state.graph_repo.store.nodes)


def test_reset_without_token_is_denied_and_changes_nothing(client: TestClient):
    client.app.state.settings.OPS_TOKEN = TOKEN
    before = _node_count(client)
    assert before > 0

    assert client.delete("/api/graph/reset").status_code == 401
    assert client.delete("/api/graph/reset", headers={"X-Ops-Token": "wrong"}).status_code == 401
    assert _node_count(client) == before


def test_reset_is_unavailable_when_no_token_is_configured(client: TestClient):
    client.app.state.settings.OPS_TOKEN = ""
    before = _node_count(client)

    resp = client.delete("/api/graph/reset", headers={"X-Ops-Token": "anything"})

    assert resp.status_code == 503
    assert _node_count(client) == before


def test_reset_with_token_clears_the_in_memory_graph(client: TestClient):
    client.app.state.settings.OPS_TOKEN = TOKEN

    resp = client.delete("/api/graph/reset", headers={"X-Ops-Token": TOKEN})

    assert resp.status_code == 200
    assert resp.json()["mode"] == "memory"
    assert _node_count(client) == 0


class _RecordingStore:
    def __init__(self):
        self.queries = []

    def run_query(self, query, params=None):
        self.queries.append(query)
        return []


class _FakeNeo4jRepo:
    """Stands in for a real database: records what would have been executed."""
    is_memory = False

    def __init__(self):
        self.store = _RecordingStore()

    def seed_demo_data(self):  # pragma: no cover - never reached in these tests
        raise AssertionError("seeding must not happen")


def test_neo4j_wipe_needs_the_token_and_a_typed_confirmation(client: TestClient):
    client.app.state.settings.OPS_TOKEN = TOKEN
    fake = _FakeNeo4jRepo()
    client.app.state.graph_repo = fake

    assert client.delete("/api/graph/reset").status_code == 401
    assert fake.store.queries == []

    no_confirm = client.delete("/api/graph/reset", headers={"X-Ops-Token": TOKEN})
    assert no_confirm.status_code == 400
    assert "confirm=WIPE" in no_confirm.json()["detail"]
    assert fake.store.queries == []

    ok = client.delete("/api/graph/reset", params={"confirm": "WIPE"}, headers={"X-Ops-Token": TOKEN})
    assert ok.status_code == 200
    assert fake.store.queries == ["MATCH (n) DETACH DELETE n"]
