import pytest

from graph.memory import MemoryGraphStore
from graph.repo import GraphRepository
from integrity.validity import is_current, superseded_by


def _repo(*ids) -> GraphRepository:
    repo = GraphRepository(MemoryGraphStore())
    for rid in ids:
        repo.create_service_record({"record_id": rid, "asset_key": "N1", "occurred_at": "2025-01-01", "text": "t"})
    return repo


def _edges(repo, rel="SUPERSEDES"):
    return [e for e in repo.store.edges if e["type"] == rel]


def test_repeated_link_is_one_edge_and_keeps_created_at():
    repo = _repo("NEW1", "OLD1")
    repo.link_record_supersedes("NEW1", "OLD1", "same", 0.5, "first")
    first = repo.get_supersedes_link("NEW1", "OLD1")
    repo.link_record_supersedes("NEW1", "OLD1", "different", 0.9, "second", method="human", decided_by="amy")
    second = repo.get_supersedes_link("NEW1", "OLD1")
    assert len(_edges(repo)) == 1
    assert second["created_at"] == first["created_at"]
    assert second["rationale"] == "second" and second["method"] == "human"


def test_properties_round_trip():
    repo = _repo("NEW1", "OLD1")
    repo.link_record_supersedes(
        "NEW1", "OLD1", "same", 0.8, "why", method="explicit_citation",
        model_version="m1", decided_by="amy", decided_at="2025-02-01T00:00:00+00:00",
    )
    link = repo.get_supersedes_link("NEW1", "OLD1")
    assert link == {
        "scope": "same", "confidence": 0.8, "rationale": "why", "created_at": link["created_at"],
        "method": "explicit_citation", "model_version": "m1", "decided_by": "amy",
        "decided_at": "2025-02-01T00:00:00+00:00",
    }
    assert repo.get_supersedes_link("OLD1", "NEW1") is None


def test_link_written_without_provenance_reports_model():
    repo = _repo("NEW1", "OLD1")
    repo.link_record_supersedes("NEW1", "OLD1", "same", 0.5, "r")
    assert repo.get_supersedes_link("NEW1", "OLD1")["method"] == "model"
    _edges(repo)[0]["properties"].pop("method")
    assert repo.get_supersedes_link("NEW1", "OLD1")["method"] == "model"


def test_unknown_method_is_rejected():
    repo = _repo("NEW1", "OLD1")
    with pytest.raises(ValueError):
        repo.link_record_supersedes("NEW1", "OLD1", "same", 0.5, "r", method="guess")


def test_unlink_returns_one_then_zero():
    repo = _repo("NEW1", "OLD1")
    repo.link_record_supersedes("NEW1", "OLD1", "same", 0.5, "r")
    assert repo.unlink_record_supersedes("NEW1", "OLD1") == 1
    assert repo.unlink_record_supersedes("NEW1", "OLD1") == 0
    assert repo.get_supersedes_link("NEW1", "OLD1") is None


def test_rejected_pair_is_reported_once():
    repo = _repo("NEW1", "OLD1", "OLD2")
    repo.link_record_not_supersedes("NEW1", "OLD1", by="amy", at="t1")
    repo.link_record_not_supersedes("NEW1", "OLD1", by="bob", at="t2")
    assert len(_edges(repo, "NOT_SUPERSEDES")) == 1
    assert repo.rejected_prior_ids("NEW1") == {"OLD1"}
    assert repo.rejected_prior_ids("OLD1") == set()


def test_list_links_filters_on_old_end_and_empty_input():
    repo = _repo("NEW1", "OLD1", "OLD2")
    repo.link_record_supersedes("NEW1", "OLD1", "same", 0.5, "r")
    repo.link_record_supersedes("NEW1", "OLD2", "same", 0.5, "r")
    links = repo.list_supersedes_links(["OLD1"])
    assert [(l["old_record_id"], l["new_record_id"]) for l in links] == [("OLD1", "NEW1")]
    assert repo.list_supersedes_links([]) == []


def test_validity_ignores_status_string():
    repo = _repo("NEW1", "OLD1", "LONE")
    repo.link_record_supersedes("NEW1", "OLD1", "same", 0.5, "r")
    sup = superseded_by(repo, ["NEW1", "OLD1", "LONE"])
    assert sup == {"OLD1": "NEW1"}
    assert is_current({"record_id": "LONE", "status": "superseded"}, sup) is True
    assert is_current({"record_id": "OLD1", "status": "accepted"}, sup) is False


def _link(repo, new, method, decided_at="", created=None):
    repo.link_record_supersedes(new, "OLD1", "same", 0.5, "r", method=method, decided_at=decided_at)
    if created:
        repo.store._link_edge("SUPERSEDES", new, "OLD1")["properties"]["created_at"] = created


def test_tie_break_method_order():
    repo = _repo("OLD1", "A", "B", "C")
    _link(repo, "C", "model")
    _link(repo, "B", "explicit_citation")
    assert superseded_by(repo, ["OLD1"]) == {"OLD1": "B"}
    _link(repo, "A", "human", decided_at="2020-01-01T00:00:00+00:00")
    assert superseded_by(repo, ["OLD1"]) == {"OLD1": "A"}


def test_tie_break_latest_then_smallest_id():
    repo = _repo("OLD1", "A", "B", "C")
    _link(repo, "A", "model", created="2025-01-01T00:00:00+00:00")
    _link(repo, "B", "model", created="2025-03-01T00:00:00+00:00")
    assert superseded_by(repo, ["OLD1"]) == {"OLD1": "B"}
    _link(repo, "C", "model", created="2025-03-01T00:00:00+00:00")
    assert superseded_by(repo, ["OLD1"]) == {"OLD1": "B"}


def test_decided_at_beats_created_at_for_recency():
    repo = _repo("OLD1", "A", "B")
    _link(repo, "A", "human", decided_at="2025-05-01T00:00:00+00:00", created="2025-01-01T00:00:00+00:00")
    _link(repo, "B", "human", created="2025-03-01T00:00:00+00:00")
    assert superseded_by(repo, ["OLD1"]) == {"OLD1": "A"}


# ---- Cypher path: a fake store records queries and returns canned rows ----

class FakeStore:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    def run_query(self, query, parameters=None):
        self.calls.append((query, parameters))
        return self.rows


def _cypher_repo(rows=None):
    repo = GraphRepository(FakeStore(rows))
    assert not repo.is_memory
    return repo


def test_cypher_link_sends_all_parameters_and_merges():
    repo = _cypher_repo()
    repo.link_record_supersedes("N", "O", "same", 0.7, "why", method="human", model_version="v", decided_by="amy", decided_at="t")
    query, params = repo.store.calls[0]
    assert "MERGE (new)-[r:SUPERSEDES]->(old)" in query and "ON CREATE SET r.created_at" in query
    assert "ServiceRecord {record_id: $nid}" in query and "ServiceRecord {record_id: $oid}" in query
    assert {k: params[k] for k in params if k != "now"} == {
        "nid": "N", "oid": "O", "scope": "same", "confidence": 0.7, "rationale": "why",
        "method": "human", "model_version": "v", "decided_by": "amy", "decided_at": "t",
    }
    assert params["now"]


def test_cypher_link_rejects_unknown_method_without_querying():
    repo = _cypher_repo()
    with pytest.raises(ValueError):
        repo.link_record_supersedes("N", "O", "s", 0.1, "r", method="x")
    assert repo.store.calls == []


def test_cypher_unlink_returns_deleted_count():
    repo = _cypher_repo([{"deleted": 1}])
    assert repo.unlink_record_supersedes("N", "O") == 1
    query, params = repo.store.calls[0]
    assert "DELETE r" in query and params == {"nid": "N", "oid": "O"}
    assert _cypher_repo([]).unlink_record_supersedes("N", "O") == 0


def test_cypher_get_link_maps_row_and_defaults_method():
    row = {"scope": "same", "confidence": 0.5, "rationale": "r", "created_at": "c",
           "method": None, "model_version": None, "decided_by": None, "decided_at": None}
    repo = _cypher_repo([row])
    link = repo.get_supersedes_link("N", "O")
    assert link["method"] == "model" and link["model_version"] == "" and link["created_at"] == "c"
    assert repo.store.calls[0][1] == {"nid": "N", "oid": "O"}
    assert _cypher_repo([]).get_supersedes_link("N", "O") is None


def test_cypher_list_links_is_one_query_and_empty_skips_it():
    row = {"old_record_id": "O1", "new_record_id": "N1", "scope": "same", "confidence": 0.5,
           "rationale": "r", "created_at": "c", "method": "human", "model_version": "",
           "decided_by": "amy", "decided_at": "t"}
    repo = _cypher_repo([row])
    links = repo.list_supersedes_links(["O1", "O2"])
    assert len(repo.store.calls) == 1
    assert repo.store.calls[0][1] == {"oids": ["O1", "O2"]}
    assert links[0]["old_record_id"] == "O1" and links[0]["new_record_id"] == "N1" and links[0]["method"] == "human"
    assert repo.list_supersedes_links([]) == [] and len(repo.store.calls) == 1


def test_cypher_not_supersedes_and_rejected_ids():
    repo = _cypher_repo([{"record_id": "O1"}, {"record_id": "O2"}])
    repo.link_record_not_supersedes("N", "O1", by="amy", at="t")
    query, params = repo.store.calls[0]
    assert "MERGE (new)-[r:NOT_SUPERSEDES]->(old)" in query
    assert params == {"nid": "N", "oid": "O1", "by": "amy", "at": "t"}
    assert repo.rejected_prior_ids("N") == {"O1", "O2"}
    assert repo.store.calls[1][1] == {"nid": "N"}
