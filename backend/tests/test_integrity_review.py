"""Review decisions change the graph, and the review screen reads a stored proposal."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from db.models.identity import AuditEvent
from db.models.integrity import ReviewDecision
from domains.maintenance import MaintenanceDomainAdapter
from integrity import apply
from integrity.validity import superseded_by
from services import conflict_engine
from services.conflict_engine import find_candidate_pairs, process_record
from tests.conftest import _build_test_app
from tests.test_auth_rbac import ADMIN_EMAIL, ADMIN_PASS, _auth_settings, _invite_and_accept, _login


class ExplodingService:
    """A model service that fails the test if anything calls it."""
    is_live = True
    model = "must-not-be-called"

    def __getattr__(self, name):
        raise AssertionError(f"the model service was used: {name}")


def _seed(repo):
    asset = repo.find_or_create_asset("N900RV", {"make": "Airbus", "model": "A321"})
    repo.create_service_record({
        "record_id": "PRIOR1", "asset_key": "N900RV", "occurred_at": "2025-03-01",
        "submitted_at": "2025-03-01T09:00:00+00:00", "part_name": "Pump", "jasc_code": "2910",
        "part_location": "Left", "part_condition": "Leaking", "text": "pump leaking",
    })
    repo.update_service_record("PRIOR1", {"status": "scored", "analysis_state": "scored"})
    repo.create_service_record({
        "record_id": "NEW1", "asset_key": "N900RV", "occurred_at": "2025-03-01",
        "submitted_at": "2025-03-08T09:00:00+00:00", "part_name": "pump ", "jasc_code": "2920",
        "part_location": "LEFT", "part_condition": "Replaced", "text": "pump replaced",
    })
    repo.update_service_record("NEW1", {
        "status": "needs_review", "analysis_state": "needs_review", "confidence": 0.62,
        "classification_label": "supersedes", "classification_rationale": "replaced",
        "analysis_method": "llm", "proposed_prior_id": "PRIOR1", "integrity_p": 0.61,
        "integrity_model_version": "handweighted-v0",
    })
    for rid in ("PRIOR1", "NEW1"):
        repo.link_record_about_asset(rid, asset["id"])


@pytest.fixture
def env(tmp_path):
    app = _build_test_app(_auth_settings(tmp_path))
    with TestClient(app) as tc:
        repo = app.state.graph_repo
        _seed(repo)
        admin_token = _login(tc, ADMIN_EMAIL, ADMIN_PASS)["access_token"]
        sup = _invite_and_accept(tc, admin_token, email="sup@halite.pk", full_name="Sam Super", role="supervisor")
        tech = _invite_and_accept(tc, admin_token, email="tech@halite.pk", full_name="Tia Tech", role="technician")
        yield {
            "tc": tc, "app": app, "repo": repo,
            "sup": {"Authorization": f"Bearer {sup['access_token']}"},
            "tech": {"Authorization": f"Bearer {tech['access_token']}"},
            "sup_id": sup["user"]["id"],
        }


def _rows(app, model):
    with app.state.rel_store.session_scope() as db:
        return list(db.scalars(select(model)))


def _review_audit(app, action):
    with app.state.rel_store.session_scope() as db:
        return [e for e in db.scalars(select(AuditEvent)) if e.action == action]


def test_accepting_a_queued_supersession_creates_a_human_link(env):
    resp = env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={"note": "agreed"}, headers=env["sup"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["link"] == "created" and body["prior_record_id"] == "PRIOR1"
    link = env["repo"].get_supersedes_link("NEW1", "PRIOR1")
    assert link["method"] == "human" and link["decided_by"] == env["sup_id"] and link["scope"] == "supersedes"
    assert superseded_by(env["repo"], ["PRIOR1"]) == {"PRIOR1": "NEW1"}


def test_accepting_an_automatic_link_confirms_it_and_keeps_its_method(env):
    repo = env["repo"]
    apply.link_supersedes(repo, "NEW1", "PRIOR1", scope="supersedes", confidence=0.7, rationale="r",
                          method="model", model_version="m1")
    repo.update_service_record("NEW1", {"status": "auto_accepted"})
    body = env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={}, headers=env["sup"]).json()
    assert body["link"] == "confirmed"
    link = repo.get_supersedes_link("NEW1", "PRIOR1")
    assert link["method"] == "model" and link["model_version"] == "m1"
    assert link["decided_by"] == env["sup_id"] and link["decided_at"]


def test_rejecting_removes_the_link_restores_the_prior_and_the_pair_never_returns(env):
    repo = env["repo"]
    apply.link_supersedes(repo, "NEW1", "PRIOR1", scope="supersedes", confidence=0.7, rationale="r", method="model")
    repo.update_service_record("NEW1", {"status": "auto_accepted"})
    assert repo.get_service_record("PRIOR1")["status"] == "superseded"

    body = env["tc"].post("/api/maintenance/review-queue/NEW1/reject", json={"note": "different pump"},
                          headers=env["sup"]).json()
    assert body["link"] == "removed" and body["status"] == "rejected"
    assert repo.get_supersedes_link("NEW1", "PRIOR1") is None
    assert repo.get_service_record("PRIOR1")["status"] == "scored"
    assert superseded_by(repo, ["PRIOR1"]) == {}

    again = process_record(repo, ExplodingService(), MaintenanceDomainAdapter(), "NEW1", allow_stub=True)
    assert again["skipped"] == "reviewed"
    forced = process_record(repo, None, MaintenanceDomainAdapter(), "NEW1", allow_stub=True, force=True,
                            analysis_mode="legacy")
    assert forced["proposed_prior_id"] == ""
    assert find_candidate_pairs(repo, "NEW1") == []


@pytest.mark.parametrize("action,decision,payload", [
    ("accept", "accepted", {"note": "ok"}),
    ("reject", "rejected", {"note": "no"}),
])
def test_a_decision_writes_one_row_and_one_audit_event_carrying_the_prior(env, action, decision, payload):
    env["tc"].post(f"/api/maintenance/review-queue/NEW1/{action}", json=payload, headers=env["sup"])
    rows = _rows(env["app"], ReviewDecision)
    assert len(rows) == 1
    row = rows[0]
    assert (row.record_id, row.prior_record_id, row.decision, row.note) == ("NEW1", "PRIOR1", decision, payload["note"])
    assert (row.reviewer_id, row.reviewer_role) == (env["sup_id"], "supervisor")
    assert row.model_p == 0.61 and row.model_version == "handweighted-v0"
    events = _review_audit(env["app"], f"maintenance.review.{decision}")
    assert len(events) == 1 and '"prior_record_id": "PRIOR1"' in events[0].metadata_json


def test_the_old_response_keys_are_still_present(env):
    body = env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={"note": "ok"}, headers=env["sup"]).json()
    assert {"record_id", "status", "record", "prior_record_id", "link"} <= set(body)
    assert body["record"]["status"] == "accepted" and body["record"]["reviewed_by_email"] == "sup@halite.pk"


def test_the_proposal_endpoint_returns_the_stored_prior_without_the_model(env, monkeypatch):
    env["app"].state.groq_service = ExplodingService()
    monkeypatch.setattr(conflict_engine, "classify_conflict",
                        lambda *a, **k: pytest.fail("classify_conflict was called"))
    resp = env["tc"].get("/api/maintenance/review-queue/NEW1/proposal", headers=env["tech"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["proposal_source"] == "stored" and body["proposed_prior"]["record_id"] == "PRIOR1"
    assert body["label"] == "supersedes" and body["method"] == "llm" and body["link"] is None
    assert body["model_version"] == "handweighted-v0" and body["cited_record_ids"] == []
    assert body["changed_fields"] == [
        {"field": "jasc_code", "prior": "2910", "new": "2920"},
        {"field": "part_condition", "prior": "Leaking", "new": "Replaced"},
    ]


def test_the_proposal_of_an_old_record_is_recomputed_without_the_model(env):
    env["repo"].update_service_record("NEW1", {"proposed_prior_id": None})
    body = env["tc"].get("/api/maintenance/review-queue/NEW1/proposal", headers=env["sup"]).json()
    assert body["proposal_source"] == "recomputed" and body["proposed_prior"]["record_id"] == "PRIOR1"


def test_a_record_with_no_prior_has_source_none_and_an_unknown_record_is_404(env):
    env["repo"].update_service_record("NEW1", {"proposed_prior_id": ""})
    body = env["tc"].get("/api/maintenance/review-queue/NEW1/proposal", headers=env["sup"]).json()
    assert body["proposal_source"] == "none" and body["proposed_prior"] is None and body["changed_fields"] == []
    assert env["tc"].get("/api/maintenance/review-queue/NOPE/proposal", headers=env["sup"]).status_code == 404


def test_a_technician_can_read_a_proposal_but_not_decide(env):
    assert env["tc"].get("/api/maintenance/review-queue/NEW1/proposal", headers=env["tech"]).status_code == 200
    assert env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={}, headers=env["tech"]).status_code == 403
    assert env["tc"].post("/api/maintenance/review-queue/NEW1/reject", json={"note": "x"},
                          headers=env["tech"]).status_code == 403
    assert env["repo"].get_service_record("NEW1")["status"] == "needs_review"


def test_accepting_a_label_that_is_not_a_supersession_links_nothing(env):
    env["repo"].update_service_record("NEW1", {"classification_label": "contradicts"})
    body = env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={}, headers=env["sup"]).json()
    assert body["link"] == "none" and env["repo"].get_supersedes_link("NEW1", "PRIOR1") is None


def test_accepting_acts_on_the_prior_the_reviewer_was_shown_for_an_old_record(env):
    env["repo"].update_service_record("NEW1", {"proposed_prior_id": None})
    body = env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={}, headers=env["sup"]).json()
    assert body["prior_record_id"] == "PRIOR1" and body["link"] == "created"


def test_an_audit_failure_does_not_fail_the_decision(env, monkeypatch):
    import services.auth_service as auth_service
    monkeypatch.setattr(auth_service, "record_audit_event", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db")))
    resp = env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={}, headers=env["sup"])
    assert resp.status_code == 200
    assert len(_rows(env["app"], ReviewDecision)) == 1


def test_the_link_a_reviewer_creates_or_removes_is_audited_in_their_name(env):
    """The review event covers the reviewed record; the link and the prior's status change need their own."""
    env["tc"].post("/api/maintenance/review-queue/NEW1/accept", json={"note": "agreed"}, headers=env["sup"])
    created = _review_audit(env["app"], "integrity.link.created")
    assert [(e.target_id, e.actor_user_id) for e in created] == [("NEW1", env["sup_id"])]
    prior_changes = [e for e in _review_audit(env["app"], "integrity.status.changed") if e.target_id == "PRIOR1"]
    assert len(prior_changes) == 1 and prior_changes[0].actor_user_id == env["sup_id"]


def test_a_typed_in_report_that_cites_an_earlier_one_is_linked_at_once_without_the_model(env):
    """The form sends an ISO date; the route used to hand it to an importer that reads MM/DD/YYYY,
    so the record was skipped and the request failed. The test app's model is not live, so a 200
    here also proves rule R1 asked no model."""
    resp = env["tc"].post("/api/maintenance/records", headers=env["tech"], json={
        "tail_number": "N900RV", "date": "2025-03-01", "part_name": "Fuel pump", "condition": "Replaced",
        "location": "Left", "jasc_code": "2910",
        "discrepancy": "SUPPLEMENTAL REPORT FOR (PRIOR1): found pump failed, removed and replaced.",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status_applied"] == "auto_accepted" and body["proposed_prior_id"] == "PRIOR1"
    link = env["repo"].get_supersedes_link(body["record_id"], "PRIOR1")
    assert link["method"] == "explicit_citation"
    assert env["repo"].get_service_record(body["record_id"])["submitted_at"]  # stamped at entry


def test_a_typed_in_report_with_an_unreadable_date_is_refused_clearly(env):
    resp = env["tc"].post("/api/maintenance/records", headers=env["tech"], json={
        "tail_number": "N900RV", "date": "yesterday", "discrepancy": "pump leaking",
    })
    assert resp.status_code == 422 and "date" in resp.json()["detail"]
