import pytest

from graph.memory import MemoryGraphStore
from graph.repo import GraphRepository
from integrity import apply


def _repo(records: dict) -> GraphRepository:
    repo = GraphRepository(MemoryGraphStore())
    for rid, extra in records.items():
        repo.create_service_record({"record_id": rid, "asset_key": "N1", "occurred_at": "2025-01-01",
                                    "submitted_at": "2025-01-01T10:00:00+00:00", "text": "t", **extra})
    return repo


class Audit:
    def __init__(self):
        self.calls = []

    def __call__(self, action, record_id, metadata):
        self.calls.append((action, record_id, metadata))


@pytest.mark.parametrize("record,expected", [
    ({"analysis_state": "reviewed"}, True),
    ({"status": "accepted"}, True),
    ({"status": "rejected"}, True),
    ({"status": "auto_accepted", "analysis_state": "scored"}, False),
    ({"status": "superseded"}, False),
    (None, False),
])
def test_human_decided_means_reviewed_accepted_or_rejected(record, expected):
    assert apply.is_human_decided(record) is expected


def test_superseding_then_unlinking_restores_the_old_status():
    repo = _repo({"NEW1": {}, "OLD1": {"status": "needs_review"}})
    audit = Audit()
    assert apply.link_supersedes(repo, "NEW1", "OLD1", scope="supersedes", confidence=0.9,
                                 rationale="r", method="model", model_version="m", audit=audit)
    old = repo.get_service_record("OLD1")
    assert old["status"] == "superseded" and old["status_before_superseded"] == "needs_review"
    assert audit.calls == [("integrity.link.created", "NEW1", {"prior_record_id": "OLD1", "method": "model"})]

    assert apply.unlink_supersedes(repo, "NEW1", "OLD1", audit=audit)
    assert repo.get_service_record("OLD1")["status"] == "needs_review"
    assert audit.calls[-1][0] == "integrity.link.removed"
    assert apply.unlink_supersedes(repo, "NEW1", "OLD1", audit=audit) is False


def test_relinking_keeps_the_first_remembered_status():
    repo = _repo({"NEW1": {}, "OLD1": {"status": "auto_accepted"}})
    for confidence in (0.6, 0.7):
        apply.link_supersedes(repo, "NEW1", "OLD1", scope="supersedes", confidence=confidence,
                              rationale="r", method="model")
    assert repo.get_service_record("OLD1")["status_before_superseded"] == "auto_accepted"


def test_unlinking_keeps_the_status_while_another_link_supersedes():
    repo = _repo({"NEW1": {}, "NEW2": {}, "OLD1": {"status": "scored"}})
    for new in ("NEW1", "NEW2"):
        apply.link_supersedes(repo, new, "OLD1", scope="supersedes", confidence=1.0, rationale="r", method="model")
    apply.unlink_supersedes(repo, "NEW1", "OLD1")
    assert repo.get_service_record("OLD1")["status"] == "superseded"
    apply.unlink_supersedes(repo, "NEW2", "OLD1")
    assert repo.get_service_record("OLD1")["status"] == "scored"


def test_a_human_decided_old_record_keeps_its_status():
    repo = _repo({"NEW1": {}, "OLD1": {"status": "accepted"}})
    apply.link_supersedes(repo, "NEW1", "OLD1", scope="supersedes", confidence=1.0, rationale="r", method="model")
    assert repo.get_supersedes_link("NEW1", "OLD1") is not None
    assert repo.get_service_record("OLD1")["status"] == "accepted"
    apply.unlink_supersedes(repo, "NEW1", "OLD1")
    assert repo.get_service_record("OLD1")["status"] == "accepted"


def test_a_rejected_pair_is_refused_unless_a_human_links_it():
    repo = _repo({"NEW1": {}, "OLD1": {}})
    repo.link_record_not_supersedes("NEW1", "OLD1", by="amy", at="2025-02-01T00:00:00+00:00")
    assert apply.link_supersedes(repo, "NEW1", "OLD1", scope="supersedes", confidence=1.0,
                                 rationale="r", method="model") is False
    assert repo.get_supersedes_link("NEW1", "OLD1") is None
    assert repo.get_service_record("OLD1").get("status") != "superseded"
    assert apply.link_supersedes(repo, "NEW1", "OLD1", scope="supersedes", confidence=1.0,
                                 rationale="r", method="human", decided_by="amy") is True


def test_citations_link_the_cited_report_and_store_the_ids():
    repo = _repo({
        "NEWREP001": {"submitted_at": "2025-01-05T10:00:00+00:00",
                      "text": "SUPPLEMENTAL REPORT FOR (OLDREP001) and SUPPLEMENTAL REPORT FOR (GONE00001)"},
        "OLDREP001": {},
    })
    record = repo.get_service_record("NEWREP001")
    result = apply.apply_explicit_citations(repo, record)
    assert result == {"cited_record_ids": ["OLDREP001", "GONE00001"], "linked": ["OLDREP001"],
                      "missing": ["GONE00001"], "ineligible": []}
    link = repo.get_supersedes_link("NEWREP001", "OLDREP001")
    assert (link["method"], link["confidence"], link["scope"]) == ("explicit_citation", 1.0, "supersedes")
    assert "OLDREP001" in link["rationale"]
    assert repo.get_service_record("NEWREP001")["cited_record_ids"] == ["OLDREP001", "GONE00001"]


def test_citations_name_why_a_cited_report_is_ineligible():
    repo = _repo({
        "NEWREP001": {"submitted_at": "2025-01-05T10:00:00+00:00",
                      "text": "SUPPLEMENTAL REPORT FOR (OTHERAC01) SUPPLEMENTAL REPORT FOR (LATER0001) "
                              "SUPPLEMENTAL REPORT FOR (NEWREP001)"},
        "OTHERAC01": {"asset_key": "N2"},
        "LATER0001": {"submitted_at": "2025-01-09T10:00:00+00:00"},
    })
    result = apply.apply_explicit_citations(repo, repo.get_service_record("NEWREP001"))
    assert result["linked"] == [] and result["missing"] == []
    reasons = {item["record_id"]: item["reason"] for item in result["ineligible"]}
    assert "different aircraft" in reasons["OTHERAC01"]
    assert "not submitted before" in reasons["LATER0001"]
    assert "itself" in reasons["NEWREP001"]
    assert repo.list_supersedes_links(["OTHERAC01", "LATER0001", "NEWREP001"]) == []


def test_citations_dry_run_reports_the_same_but_writes_nothing():
    repo = _repo({"NEWREP001": {"submitted_at": "2025-01-05T10:00:00+00:00",
                                "text": "SUPPLEMENTAL REPORT FOR (OLDREP001)"}, "OLDREP001": {}})
    audit = Audit()
    result = apply.apply_explicit_citations(repo, repo.get_service_record("NEWREP001"), dry_run=True, audit=audit)
    assert result["linked"] == ["OLDREP001"]
    assert repo.get_supersedes_link("NEWREP001", "OLDREP001") is None
    assert "cited_record_ids" not in repo.get_service_record("NEWREP001")
    assert audit.calls == []


def test_a_rejected_citation_is_ineligible():
    repo = _repo({"NEWREP001": {"submitted_at": "2025-01-05T10:00:00+00:00",
                                "text": "SUPPLEMENTAL REPORT FOR (OLDREP001)"}, "OLDREP001": {}})
    repo.link_record_not_supersedes("NEWREP001", "OLDREP001", by="amy", at="2025-02-01T00:00:00+00:00")
    result = apply.apply_explicit_citations(repo, repo.get_service_record("NEWREP001"))
    assert result["linked"] == [] and result["ineligible"][0]["record_id"] == "OLDREP001"


def test_record_analysis_audits_one_event_per_status_change_and_none_for_a_repeat():
    repo = _repo({"REC1": {"status": "unscored"}})
    audit = Audit()
    updates = {"status": "needs_review", "analysis_method": "llm", "confidence": 0.4}
    apply.record_analysis(repo, "REC1", updates, audit=audit)
    apply.record_analysis(repo, "REC1", updates, audit=audit)
    assert audit.calls == [("integrity.status.changed", "REC1",
                            {"from": "unscored", "to": "needs_review", "method": "llm"})]


def test_record_analysis_refuses_a_human_decision_unless_forced():
    repo = _repo({"REC1": {"status": "rejected", "analysis_state": "reviewed"}})
    audit = Audit()
    assert apply.record_analysis(repo, "REC1", {"status": "auto_accepted"}, audit=audit) is None
    assert repo.get_service_record("REC1")["status"] == "rejected" and audit.calls == []
    assert apply.record_analysis(repo, "REC1", {"status": "auto_accepted"}, force=True, audit=audit)
    assert repo.get_service_record("REC1")["status"] == "auto_accepted"
    assert len(audit.calls) == 1
