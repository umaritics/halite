import json

from domains.maintenance import MaintenanceDomainAdapter
from graph.memory import MemoryGraphStore
from graph.repo import GraphRepository
from services.conflict_engine import find_candidate_pairs, process_record


class CountingModel:
    """A live-looking stub that records how many times it was asked."""
    demo_mode = False
    fallback_invocations = 0
    is_live = True
    model = "stub-model"

    def __init__(self, label: str = "supersedes"):
        self.label = label
        self.calls = 0

    def extract_json(self, prompt, system_prompt=None, **_):
        self.calls += 1
        return json.dumps({"label": self.label, "rationale": "stub rationale"})

    chat = extract_json


class Audit:
    def __init__(self):
        self.calls = []

    def __call__(self, action, record_id, metadata):
        self.calls.append((action, record_id, metadata))

    def of(self, action):
        return [c for c in self.calls if c[0] == action]


def _repo(records: list[dict], tail: str = "N1") -> GraphRepository:
    repo = GraphRepository(MemoryGraphStore())
    assets: dict[str, dict] = {}
    for record in records:
        data = {"asset_key": tail, "occurred_at": "2025-01-01", "part_name": "PUMP",
                "jasc_code": "2913", "text": "pump seal leaking", **record}
        asset = assets.setdefault(data["asset_key"], repo.find_or_create_asset(data["asset_key"], {}))
        repo.create_service_record(data)
        repo.link_record_about_asset(data["record_id"], asset["id"])
    return repo


def _run(repo, model, record_id, **kwargs):
    return process_record(repo, model, MaintenanceDomainAdapter(), record_id, allow_stub=True, **kwargs)


def _citing_corpus() -> GraphRepository:
    return _repo([
        {"record_id": "CITED0001", "submitted_at": "2025-01-01T10:00:00+00:00", "part_name": "SEAL"},
        {"record_id": "TOPCAND01", "submitted_at": "2025-01-02T10:00:00+00:00"},
        {"record_id": "NEWREP001", "submitted_at": "2025-01-05T10:00:00+00:00",
         "text": "SUPPLEMENTAL REPORT FOR (CITED0001): pump seal replaced"},
    ])


def test_a_report_citing_an_id_is_linked_to_the_cited_report_not_the_top_candidate():
    repo, model = _citing_corpus(), CountingModel()
    result = _run(repo, model, "NEWREP001")
    assert model.calls == 0
    assert result["status_applied"] == "auto_accepted" and result["confidence"] == 1.0
    assert result["proposed_prior_id"] == "CITED0001" and result["best_prior"]["record_id"] == "CITED0001"
    assert result["classification"]["method"] == "explicit_citation"
    assert result["classification"]["model"] == "rule-R1"
    assert repo.get_supersedes_link("NEWREP001", "CITED0001")["method"] == "explicit_citation"
    assert repo.get_supersedes_link("NEWREP001", "TOPCAND01") is None
    assert repo.get_service_record("CITED0001")["status"] == "superseded"
    stored = repo.get_service_record("NEWREP001")
    assert stored["analysis_method"] == "explicit_citation" and stored["proposed_prior_id"] == "CITED0001"


def test_a_cited_id_missing_from_the_graph_gives_no_link_and_no_review():
    repo = _repo([
        {"record_id": "TOPCAND01", "submitted_at": "2025-01-02T10:00:00+00:00"},
        {"record_id": "NEWREP001", "submitted_at": "2025-01-05T10:00:00+00:00",
         "text": "SUPPLEMENTAL REPORT FOR (GONE00001): pump seal replaced"},
    ])
    model = CountingModel()
    result = _run(repo, model, "NEWREP001")
    assert model.calls == 0
    assert result["status_applied"] == "no_action" and result["route"] == "no_action"
    assert result["classification"]["label"] == "cited_prior_missing"
    assert "not in the corpus" in result["classification"]["rationale"]
    stored = repo.get_service_record("NEWREP001")
    assert stored["status"] == "no_action" and stored["analysis_state"] == "scored"
    assert stored["cited_record_ids"] == ["GONE00001"]
    assert repo.list_supersedes_links(["TOPCAND01"]) == []


def test_a_cited_report_on_a_different_aircraft_is_not_linked_by_rule():
    repo = _repo([
        {"record_id": "OTHERAC01", "asset_key": "N2", "submitted_at": "2025-01-01T10:00:00+00:00"},
        {"record_id": "NEWREP001", "submitted_at": "2025-01-05T10:00:00+00:00",
         "text": "SUPPLEMENTAL REPORT FOR (OTHERAC01): pump seal replaced"},
    ])
    result = _run(repo, CountingModel("no_conflict"), "NEWREP001")
    assert repo.get_supersedes_link("NEWREP001", "OTHERAC01") is None
    assert result["classification"].get("method") != "explicit_citation"
    assert result["citation_ineligible"][0]["record_id"] == "OTHERAC01"
    assert "different aircraft" in result["citation_ineligible"][0]["reason"]
    assert repo.get_service_record("NEWREP001")["cited_record_ids"] == ["OTHERAC01"]


def _reviewed_corpus(status: str) -> GraphRepository:
    repo = _repo([
        {"record_id": "PRIOR0001", "submitted_at": "2025-01-01T10:00:00+00:00"},
        {"record_id": "NEWREP001", "submitted_at": "2025-01-05T10:00:00+00:00",
         "status": status, "analysis_state": "reviewed", "confidence": 0.42,
         "classification_label": "supersedes"},
    ])
    repo.update_service_record("NEWREP001", {"proposed_prior_id": "PRIOR0001"})
    return repo


def test_a_reviewed_record_is_returned_untouched_and_reprocessed_when_forced():
    for status in ("accepted", "rejected"):
        repo, model, audit = _reviewed_corpus(status), CountingModel(), Audit()
        before = dict(repo.get_service_record("NEWREP001"))
        result = _run(repo, model, "NEWREP001", audit=audit)
        assert result["skipped"] == "reviewed"
        assert (result["route"], result["status_applied"], result["confidence"]) == (status, status, 0.42)
        assert result["best_prior"]["record_id"] == "PRIOR0001"
        assert model.calls == 0 and audit.calls == []
        assert repo.get_service_record("NEWREP001") == before
        assert repo.list_supersedes_links(["PRIOR0001"]) == []

        forced = _run(repo, model, "NEWREP001", force=True, audit=audit)
        assert "skipped" not in forced and model.calls > 0
        assert repo.get_service_record("NEWREP001")["status"] == "auto_accepted"
        assert len(audit.of("integrity.status.changed")) == 1


def test_a_dry_run_on_a_reviewed_record_still_computes_and_writes_nothing():
    repo, model = _reviewed_corpus("accepted"), CountingModel()
    result = _run(repo, model, "NEWREP001", dry_run=True)
    assert "skipped" not in result and model.calls > 0
    assert repo.get_service_record("NEWREP001")["status"] == "accepted"


def test_a_pair_with_a_not_supersedes_link_is_never_proposed_again():
    repo = _repo([
        {"record_id": "PRIOR0001", "submitted_at": "2025-01-01T10:00:00+00:00"},
        {"record_id": "PRIOR0002", "submitted_at": "2025-01-02T10:00:00+00:00", "part_name": "SEAL"},
        {"record_id": "NEWREP001", "submitted_at": "2025-01-05T10:00:00+00:00"},
    ])
    repo.link_record_not_supersedes("NEWREP001", "PRIOR0001", by="amy", at="2025-02-01T00:00:00+00:00")
    ids = [c["record"]["record_id"] for c in find_candidate_pairs(repo, "NEWREP001")]
    assert ids == ["PRIOR0002"]
    result = _run(repo, CountingModel(), "NEWREP001")
    assert result["proposed_prior_id"] == "PRIOR0002"


def test_exactly_one_audit_call_per_status_change_and_none_when_nothing_changes_or_in_dry_run():
    repo, model, audit = _citing_corpus(), CountingModel(), Audit()
    _run(repo, model, "NEWREP001", dry_run=True, audit=audit)
    assert audit.calls == []
    assert repo.get_service_record("NEWREP001")["status"] == "unscored"

    _run(repo, model, "NEWREP001", audit=audit)
    assert len(audit.of("integrity.status.changed")) == 1
    assert audit.of("integrity.status.changed")[0][2]["to"] == "auto_accepted"
    assert len(audit.of("integrity.link.created")) == 1
    count = len(audit.calls)

    _run(repo, model, "NEWREP001", audit=audit)
    assert len(audit.calls) == count


def test_proposed_prior_id_is_stored_and_returned_on_the_normal_path():
    repo = _repo([
        {"record_id": "PRIOR0001", "submitted_at": "2025-01-01T10:00:00+00:00"},
        {"record_id": "NEWREP001", "submitted_at": "2025-01-05T10:00:00+00:00"},
    ])
    result = _run(repo, CountingModel("supersedes"), "NEWREP001")
    stored = repo.get_service_record("NEWREP001")
    assert result["proposed_prior_id"] == stored["proposed_prior_id"] == "PRIOR0001"
    assert stored["integrity_p"] == result["confidence"]
    assert stored["integrity_model_version"] == "handweighted-v0"
    link = repo.get_supersedes_link("NEWREP001", "PRIOR0001")
    assert link["method"] == "model" and link["model_version"] == "stub-model"


def test_a_record_without_candidates_stores_an_empty_proposed_prior():
    repo = _repo([{"record_id": "ONLY00001"}])
    result = _run(repo, CountingModel(), "ONLY00001")
    assert result["proposed_prior_id"] == "" and repo.get_service_record("ONLY00001")["proposed_prior_id"] == ""


def test_same_day_reports_are_ordered_by_instant_not_by_submission_string():
    early_in_utc = "2025-01-02T12:00:00+00:00"       # 12:00Z, but sorts after the next string
    late_in_utc = "2025-01-02T09:00:00-05:00"        # 14:00Z
    repo = _repo([
        {"record_id": "FIRST0001", "submitted_at": early_in_utc},
        {"record_id": "SECOND001", "submitted_at": late_in_utc},
    ])
    later = [c["record"]["record_id"] for c in find_candidate_pairs(repo, "SECOND001")]
    earlier = [c["record"]["record_id"] for c in find_candidate_pairs(repo, "FIRST0001")]
    assert later == ["FIRST0001"]
    assert earlier == []
