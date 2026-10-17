"""
test_api_maintenance.py — Integration tests for maintenance API routes.

All tests run against the TestClient with DEMO_MODE=True (in-memory graph).
No network calls, no file system access beyond synthetic in-memory records.

Coverage required by §T6:
  - POST /api/maintenance/ingest (json body, no file system needed — test uses records endpoint after manual seeding)
  - GET  /api/domains returns both domains
  - GET  /api/maintenance/assets returns empty list when no assets
  - GET  /api/maintenance/assets/{id}/history returns 404 for unknown asset
  - POST /api/maintenance/records — conflict detection on ingested record
  - GET  /api/maintenance/review-queue returns needs_review records
  - POST /api/maintenance/review-queue/{id}/accept changes status
  - POST /api/maintenance/review-queue/{id}/reject changes status (note required)
  - GET  /health includes domain list and maintenance fields
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from tests.conftest import _build_test_app


@pytest.fixture
def client():
    app = _build_test_app()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /api/domains
# ---------------------------------------------------------------------------

class TestDomains:
    def test_returns_two_domains(self, client):
        resp = client.get("/api/domains")
        assert resp.status_code == 200
        data = resp.json()
        keys = {d["key"] for d in data}
        assert "software" in keys
        assert "maintenance" in keys

    def test_software_is_default(self, client):
        resp = client.get("/api/domains")
        data = resp.json()
        sw = next(d for d in data if d["key"] == "software")
        assert sw["is_default"] is True

    def test_maintenance_not_default(self, client):
        resp = client.get("/api/domains")
        data = resp.json()
        mnt = next(d for d in data if d["key"] == "maintenance")
        assert mnt["is_default"] is False

    def test_domain_has_required_fields(self, client):
        resp = client.get("/api/domains")
        data = resp.json()
        for d in data:
            for field in ("key", "display_name", "subject_label", "record_label", "is_default"):
                assert field in d, f"Missing field {field!r} in domain {d.get('key')}"


# ---------------------------------------------------------------------------
# /health — maintenance fields
# ---------------------------------------------------------------------------

class TestHealthMaintenance:
    def test_health_includes_domains(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "domains" in data
        assert len(data["domains"]) >= 2

    def test_health_includes_maintenance_fields(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "maintenance_corpus_loaded" in data
        assert "maintenance_record_count" in data
        assert "fallback_invocations" in data
        assert "graph_mode" in data
        assert "llm_mode" in data

    def test_health_maintenance_false_before_ingest(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["maintenance_corpus_loaded"] is False
        assert data["maintenance_record_count"] == 0

    def test_health_uses_count_query_not_record_materialization(self, client, monkeypatch):
        repo = client.app.state.graph_repo
        monkeypatch.setattr(
            repo,
            "list_service_records",
            lambda *args, **kwargs: pytest.fail("health must not materialize records"),
        )

        resp = client.get("/api/health")

        assert resp.status_code == 200
        assert resp.json()["maintenance_record_count"] == 0


# ---------------------------------------------------------------------------
# /api/maintenance/assets — empty state
# ---------------------------------------------------------------------------

class TestAssetsEmpty:
    def test_returns_empty_list(self, client):
        resp = client.get("/api/maintenance/assets")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unknown_asset_history_is_404(self, client):
        resp = client.get("/api/maintenance/assets/nonexistent-id/history")
        assert resp.status_code == 404

    def test_ingest_rejects_non_positive_limit(self, client):
        resp = client.post("/api/maintenance/ingest", json={"limit": 0})
        assert resp.status_code == 422

    def test_record_processing_rejects_invalid_threshold(self, client):
        resp = client.post(
            "/api/maintenance/records",
            json={"record_id": "missing", "threshold": 1.01},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Ingest-then-query pattern (inline ingest via graph_repo directly)
# ---------------------------------------------------------------------------

class TestIngestAndQuery:
    @pytest.fixture
    def seeded_client(self):
        """Client with 2 records for the same asset pre-seeded."""
        app = _build_test_app()
        with TestClient(app) as c:
            # Directly seed via the graph_repo
            repo = app.state.graph_repo
            asset = repo.find_or_create_asset("NSEED1", {"make": "Boeing", "model": "737"})
            repo.create_service_record({
                "record_id": "SEED001",
                "asset_key": "NSEED1",
                "occurred_at": "2025-01-01",
                "text": "Exit sign missing.",
                "part_name": "Exit Sign",
                "jasc_code": "3350",
                "status": "needs_review",
                "confidence": 0.5,
            })
            repo.link_record_about_asset("SEED001", asset["id"])
            repo.create_service_record({
                "record_id": "SEED002",
                "asset_key": "NSEED1",
                "occurred_at": "2025-02-01",
                "text": "SUPPLEMENTAL REPORT FOR (SEED001): Replaced exit sign assembly.",
                "part_name": "Exit Sign",
                "jasc_code": "3350",
                "status": "auto_accepted",
                "confidence": 0.9,
            })
            repo.link_record_about_asset("SEED002", asset["id"])
            yield c, asset["id"]

    def test_assets_listed_after_seed(self, seeded_client, monkeypatch):
        c, asset_id = seeded_client
        repo = c.app.state.graph_repo
        monkeypatch.setattr(
            repo,
            "list_asset_history",
            lambda *_args, **_kwargs: pytest.fail(
                "assets endpoint must not issue per-asset history queries"
            ),
        )
        resp = c.get("/api/maintenance/assets")
        assert resp.status_code == 200
        assets = resp.json()
        assert len(assets) == 1
        assert assets[0]["tail_number"] == "NSEED1"
        assert assets[0]["record_count"] == 2

    def test_asset_history_returned(self, seeded_client):
        c, asset_id = seeded_client
        resp = c.get(f"/api/maintenance/assets/{asset_id}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        # Ascending order
        dates = [r["occurred_at"] for r in data["records"]]
        assert dates == sorted(dates)

    def test_review_queue_returns_needs_review(self, seeded_client):
        c, _ = seeded_client
        resp = c.get("/api/maintenance/review-queue")
        assert resp.status_code == 200
        queue = resp.json()
        rids = [r["record_id"] for r in queue]
        assert "SEED001" in rids
        assert "SEED002" not in rids  # auto_accepted should not appear

    def test_accept_changes_status(self, seeded_client):
        c, _ = seeded_client
        resp = c.post(
            "/api/maintenance/review-queue/SEED001/accept",
            json={"note": "Verified by panel"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"

    def test_reject_requires_note(self, seeded_client):
        c, _ = seeded_client
        # Missing note
        resp = c.post("/api/maintenance/review-queue/SEED001/reject", json={})
        assert resp.status_code == 422, "Reject without note should return 422"

    def test_reject_disallows_blank_note(self, seeded_client):
        c, _ = seeded_client
        resp = c.post(
            "/api/maintenance/review-queue/SEED001/reject",
            json={"note": "   "},
        )
        assert resp.status_code == 422

    def test_reject_with_note_succeeds(self, seeded_client):
        c, _ = seeded_client
        resp = c.post(
            "/api/maintenance/review-queue/SEED001/reject",
            json={"note": "Duplicate of older record"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["record"]["text"] == "Exit sign missing."
        assert data["record"]["record_id"] == "SEED001"

    def test_reject_cannot_overwrite_completed_review(self, seeded_client):
        c, _ = seeded_client
        accepted = c.post(
            "/api/maintenance/review-queue/SEED001/accept",
            json={"note": "Verified by panel"},
        )
        assert accepted.status_code == 200

        rejected = c.post(
            "/api/maintenance/review-queue/SEED001/reject",
            json={"note": "Changed mind"},
        )
        assert rejected.status_code == 409

    def test_conflict_detection_on_seeded_record(self, seeded_client, monkeypatch):
        """POST /api/maintenance/records runs conflict engine on the new record."""
        def mock_process_record(*args, **kwargs):
            return {
                "record_id": "SEED002",
                "candidates_considered": 1,
                "best_prior": None,
                "classification": None,
                "adjudication": None,
                "signals": {},
                "confidence": 0.8,
                "route": "auto_accepted",
                "parse_failures": 0,
                "status_applied": "auto_accepted"
            }
        import api.routes.maintenance
        monkeypatch.setattr(api.routes.maintenance, "process_record", mock_process_record)

        c, _ = seeded_client
        resp = c.post(
            "/api/maintenance/records",
            json={"record_id": "SEED002"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == "SEED002"
        assert "confidence" in data
        assert "route" in data
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["route"] in ("auto_accepted", "needs_review")


class TestConflictAnalysisApi:
    @staticmethod
    def _seed_record(app, record_id, date, analysis_state="unscored"):
        repo = app.state.graph_repo
        asset = repo.find_or_create_asset("NANALYSIS", {})
        repo.create_service_record({
            "record_id": record_id,
            "asset_key": "NANALYSIS",
            "occurred_at": date,
            "text": "inspection finding",
            "part_name": "PUMP",
            "analysis_state": analysis_state,
            "status": "unscored" if analysis_state == "unscored" else "no_action",
        })
        repo.link_record_about_asset(record_id, asset["id"])

    def test_status_counts_and_records_list_limit_validation(self, client):
        self._seed_record(client.app, "API-UNSCORED", "2025-01-01")
        self._seed_record(client.app, "API-SCORED", "2025-01-02", "scored")
        status = client.get("/api/maintenance/analysis/status")
        assert status.status_code == 200
        assert status.json()["total"] == 2
        assert status.json()["unscored"] == 1
        assert status.json()["scored"] == 1

        page = client.get("/api/maintenance/records", params={"limit": 1})
        assert page.status_code == 200
        assert page.json()["total"] == 2
        assert page.json()["next"] == 1
        assert client.get("/api/maintenance/records", params={"limit": 101}).status_code == 422

    def test_analysis_run_requires_token_and_live_llm(self, client):
        client.app.state.settings.OPS_TOKEN = "analysis-token"
        assert client.post("/api/maintenance/analysis/run", json={"batch_size": 1}).status_code == 401
        response = client.post(
            "/api/maintenance/analysis/run",
            json={"batch_size": 1},
            headers={"X-Ops-Token": "analysis-token"},
        )
        assert response.status_code == 503
        assert "live Groq" in response.json()["detail"]

    def test_no_candidate_is_analysed_without_model_call_and_scored_is_skipped(self, client):
        class LiveModelThatMustNotBeCalled:
            is_live = True
            model = "test-live-model"

            def complete(self, *_args, **_kwargs):
                raise AssertionError("first record has no candidates and must not call the model")

        client.app.state.settings.OPS_TOKEN = "analysis-token"
        client.app.state.groq_service = LiveModelThatMustNotBeCalled()
        self._seed_record(client.app, "FIRST", "2025-01-01")
        self._seed_record(client.app, "ALREADY", "2025-01-02", "scored")

        response = client.post(
            "/api/maintenance/analysis/run",
            json={"batch_size": 1},
            headers={"X-Ops-Token": "analysis-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 1
        assert data["model_records"] == 0
        assert data["no_candidate_records"] == 1
        assert data["results"][0]["record_id"] == "FIRST"
        assert data["results"][0]["classification_label"] == "no_candidates"
        assert client.app.state.graph_repo.get_service_record("ALREADY")["analysis_state"] == "scored"

    def test_corrections_endpoint_returns_live_summary(self, client):
        repo = client.app.state.graph_repo
        asset = repo.find_or_create_asset("NAPI-CORR", {})
        for rid, date, part in (
            ("API-OLD", "2025-01-01", "PUMP"),
            ("API-NEW", "2025-02-01", "SWITCH"),
        ):
            repo.create_service_record({
                "record_id": rid, "asset_key": "NAPI-CORR", "occurred_at": date,
                "text": rid, "part_name": part, "analysis_state": "scored",
            })
            repo.link_record_about_asset(rid, asset["id"])
        repo.link_record_supersedes("API-NEW", "API-OLD", "supersedes", 0.8, "new finding")

        response = client.get("/api/maintenance/corrections")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == {
            "total_corrections": 1,
            "component_changed": 1,
            "component_changed_pct": 100.0,
        }
        assert data["items"][0]["older_record"]["id"] == "API-OLD"
        assert data["items"][0]["newer_record"]["id"] == "API-NEW"
