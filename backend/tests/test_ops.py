"""Ops routes: version is public; logs require OPS_TOKEN."""
from fastapi.testclient import TestClient


def test_ops_version_public(client: TestClient):
    resp = client.get("/api/ops/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "Halite"
    assert "git_sha" in body
    assert "ops_logs_enabled" in body


def test_ops_logs_requires_token(client: TestClient):
    client.app.state.settings.OPS_TOKEN = "test-ops-token"

    denied = client.get("/api/ops/logs")
    assert denied.status_code == 401

    ok = client.get("/api/ops/logs", headers={"X-Ops-Token": "test-ops-token"})
    assert ok.status_code == 200
    assert "lines" in ok.json()


def test_ops_logs_unconfigured(client: TestClient):
    client.app.state.settings.OPS_TOKEN = ""
    resp = client.get("/api/ops/logs", headers={"X-Ops-Token": "anything"})
    assert resp.status_code == 503
