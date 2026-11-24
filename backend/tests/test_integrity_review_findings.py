"""Regression tests for the review findings on the integrity branch."""
import json

from domains.maintenance import MaintenanceDomainAdapter
from graph.memory import MemoryGraphStore
from graph.repo import GraphRepository
from integrity import apply
from integrity.citations import parse_citations
from integrity.proposal import resolve_prior
from services.conflict_engine import process_record


class Model:
    demo_mode = False
    fallback_invocations = 0
    is_live = True
    model = "stub-model"

    def __init__(self, label="supersedes"):
        self.label = label

    def extract_json(self, prompt, system_prompt=None, **_):
        return json.dumps({"label": self.label, "rationale": "stub"})

    chat = extract_json


class Audit:
    def __init__(self):
        self.calls = []

    def __call__(self, action, record_id, metadata):
        self.calls.append((action, record_id, metadata))


REVIEWER = {"id": "u1", "name": "Rev", "email": "r@x", "role": "supervisor"}


def _repo(records):
    repo = GraphRepository(MemoryGraphStore())
    asset = repo.find_or_create_asset("N1", {})
    for rid, extra in records.items():
        repo.create_service_record({
            "record_id": rid, "asset_key": "N1", "occurred_at": "2025-01-01", "part_name": "PUMP",
            "jasc_code": "2913", "submitted_at": "2025-01-01T10:00:00+00:00", "text": "pump seal leaking", **extra,
        })
        repo.link_record_about_asset(rid, asset["id"])
    return repo


def _two_cited():
    return _repo({
        "AAAAAA1": {}, "BBBBBB1": {},
        "NEW0001": {"submitted_at": "2025-01-05T10:00:00+00:00",
                    "text": "SUPPLEMENTAL REPORT FOR AAAAAA1 and SUPPLEMENTAL REPORT FOR BBBBBB1"},
    })


def _process(repo, record_id, model=None, **kw):
    return process_record(repo, model or Model(), MaintenanceDomainAdapter(), record_id, allow_stub=True, **kw)


def test_rejecting_a_report_that_cites_two_priors_removes_both_links():
    repo = _two_cited()
    _process(repo, "NEW0001")
    assert repo.superseded_prior_ids("NEW0001") == ["AAAAAA1", "BBBBBB1"]
    apply.reject_proposal(repo, "NEW0001", reviewer=REVIEWER, note="no")
    assert repo.superseded_prior_ids("NEW0001") == []
    assert repo.rejected_prior_ids("NEW0001") == {"AAAAAA1", "BBBBBB1"}
    assert repo.get_service_record("BBBBBB1")["status"] == "unscored"


def test_accepting_a_report_that_cites_two_priors_confirms_both_links():
    repo = _two_cited()
    _process(repo, "NEW0001")
    apply.accept_proposal(repo, "NEW0001", reviewer=REVIEWER, note="ok")
    for prior in ("AAAAAA1", "BBBBBB1"):
        link = repo.get_supersedes_link("NEW0001", prior)
        assert link["decided_by"] == "u1" and link["method"] == "explicit_citation"


def test_a_record_that_already_supersedes_a_report_keeps_that_prior_instead_of_recomputing():
    repo = _repo({"X0000001": {}, "Y0000001": {"part_name": "PUMP"},
                  "NEW0001": {"submitted_at": "2025-01-05T10:00:00+00:00"}})
    apply.link_supersedes(repo, "NEW0001", "X0000001", scope="supersedes", confidence=0.9,
                          rationale="r", method="model")
    assert resolve_prior(repo, repo.get_service_record("NEW0001")) == ("X0000001", "stored")


def test_reprocessing_drops_a_model_link_to_a_prior_that_is_no_longer_proposed():
    repo = _repo({"X0000001": {"submitted_at": "2025-01-01T10:00:00+00:00"},
                  "NEW0001": {"submitted_at": "2025-01-05T10:00:00+00:00"}})
    audit = Audit()
    _process(repo, "NEW0001", audit=audit)
    assert repo.superseded_prior_ids("NEW0001") == ["X0000001"]
    _process(repo, "NEW0001", Model("no_conflict"), audit=audit)
    assert repo.superseded_prior_ids("NEW0001") == []
    assert repo.get_service_record("X0000001")["status"] == "unscored"


def test_reprocessing_keeps_citation_and_human_links():
    repo = _repo({"X0000001": {}, "NEW0001": {"submitted_at": "2025-01-05T10:00:00+00:00"}})
    apply.link_supersedes(repo, "NEW0001", "X0000001", scope="supersedes", confidence=1.0, rationale="r",
                          method="human", decided_by="u1", decided_at="now")
    apply.drop_stale_model_links(repo, "NEW0001", set())
    assert repo.superseded_prior_ids("NEW0001") == ["X0000001"]


def test_the_prior_status_change_is_audited_even_when_the_link_already_existed():
    repo = _repo({"NEW0001": {}, "OLD0001": {"status": "needs_review"}})
    audit = Audit()
    kwargs = dict(scope="supersedes", confidence=0.9, rationale="r", method="model", audit=audit)
    apply.link_supersedes(repo, "NEW0001", "OLD0001", **kwargs)
    repo.update_service_record("OLD0001", {"status": "needs_review"})
    apply.link_supersedes(repo, "NEW0001", "OLD0001", **kwargs)
    changes = [c for c in audit.calls if c[0] == "integrity.status.changed"]
    assert [(c[2]["from"], c[2]["to"]) for c in changes] == [("needs_review", "superseded")] * 2
    assert len([c for c in audit.calls if c[0] == "integrity.link.created"]) == 1


def test_linking_from_a_record_that_does_not_exist_changes_nothing():
    repo = _repo({"OLD0001": {"status": "scored"}})
    audit = Audit()
    assert apply.link_supersedes(repo, "GHOST", "OLD0001", scope="supersedes", confidence=0.9,
                                 rationale="r", method="model", audit=audit) is False
    assert repo.get_service_record("OLD0001")["status"] == "scored"
    assert audit.calls == []


def test_an_ordinary_word_after_the_phrase_is_not_a_cited_id_and_the_model_still_runs():
    assert parse_citations("Supplemental report for engine failure on ...") == []
    repo = _repo({"X0000001": {}, "NEW0001": {"submitted_at": "2025-01-05T10:00:00+00:00",
                                              "text": "Supplemental report for engine failure on pump seal leaking"}})
    result = _process(repo, "NEW0001")
    assert result["classification"]["label"] != "cited_prior_missing"
