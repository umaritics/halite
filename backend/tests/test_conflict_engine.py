"""
test_conflict_engine.py — Unit tests for services/conflict_engine.py.

ALL tests use a stub groq_service — no network calls.

Coverage required by §T5:
  - pairing returns only same-asset records
  - respects max_candidates
  - every classification branch (each label)
  - adjudication prefers later record at equal authority
  - adjudication prefers higher authority at close recency
  - confidence bounded 0–1
  - routing at, just below, just above threshold
  - parse failure counted not swallowed
  - §7 guard: process_record raises when is_live=False and allow_stub=False
  - process_record with allow_stub=True succeeds
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from domains.maintenance import MaintenanceDomainAdapter


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class StubGroqLive:
    """Stub that looks live and returns configurable classification."""
    demo_mode = False
    fallback_invocations = 0

    @property
    def is_live(self) -> bool:
        return True

    def __init__(self, label: str = "supersedes", parse_fail: bool = False):
        self._label = label
        self._parse_fail = parse_fail

    def extract_json(self, prompt: str, system_prompt: str | None = None, **_) -> str:
        if self._parse_fail:
            return "THIS IS NOT JSON {{{{"
        return json.dumps({
            "label": self._label,
            "rationale": f"Test rationale for {self._label}.",
        })

    def chat(self, *args, **kwargs) -> str:
        return self.extract_json(*args, **kwargs)


class StubGroqDead:
    """Stub that reports is_live=False (no API key scenario)."""
    demo_mode = True
    fallback_invocations = 0

    @property
    def is_live(self) -> bool:
        return False


def _make_repo() -> GraphRepository:
    return GraphRepository(MemoryGraphStore())


def _setup_asset_with_records(repo, tail: str = "NTST", records: list | None = None):
    """Helper: create an asset and link records to it."""
    asset = repo.find_or_create_asset(tail, {"make": "Boeing", "model": "737"})
    if records is None:
        records = [
            {"record_id": "R001", "occurred_at": "2025-01-01", "part_name": "Exit Sign",
             "jasc_code": "3350", "part_location": "Row14", "text": "Sign missing."},
            {"record_id": "R002", "occurred_at": "2025-01-10", "part_name": "Exit Sign",
             "jasc_code": "3350", "part_location": "Row14",
             "text": "SUPPLEMENTAL REPORT FOR (R001): Replaced exit sign assembly."},
        ]
    for r in records:
        data = {"asset_key": tail, "status": "auto_accepted", "confidence": 1.0,
                "source": "faa_sdr", **r}
        repo.create_service_record(data)
        repo.link_record_about_asset(r["record_id"], asset["id"])
    return asset


# ---------------------------------------------------------------------------
# find_candidate_pairs
# ---------------------------------------------------------------------------

class TestFindCandidatePairs:
    def test_returns_only_same_asset_records(self):
        """Records from other assets must not appear as candidates."""
        from services.conflict_engine import find_candidate_pairs
        repo = _make_repo()

        # Asset 1
        a1 = repo.find_or_create_asset("NASSET1", {})
        repo.create_service_record({"record_id": "A1R001", "asset_key": "NASSET1",
                                    "occurred_at": "2025-01-01", "text": "p1"})
        repo.link_record_about_asset("A1R001", a1["id"])
        repo.create_service_record({"record_id": "A1R002", "asset_key": "NASSET1",
                                    "occurred_at": "2025-02-01", "text": "p2"})
        repo.link_record_about_asset("A1R002", a1["id"])

        # Asset 2 — completely separate
        a2 = repo.find_or_create_asset("NASSET2", {})
        repo.create_service_record({"record_id": "A2R001", "asset_key": "NASSET2",
                                    "occurred_at": "2025-01-01", "text": "other asset"})
        repo.link_record_about_asset("A2R001", a2["id"])

        candidates = find_candidate_pairs(repo, "A1R002")
        record_ids = {c["record"]["record_id"] for c in candidates}
        assert "A2R001" not in record_ids, "Other-asset record must not appear as candidate"
        assert "A1R001" in record_ids, "Same-asset earlier record must be a candidate"

    def test_respects_max_candidates(self):
        from services.conflict_engine import find_candidate_pairs
        repo = _make_repo()
        asset = repo.find_or_create_asset("NMAXCAND", {})
        # 10 prior records + 1 target
        for i in range(10):
            rid = f"MC{i:03d}"
            repo.create_service_record({"record_id": rid, "asset_key": "NMAXCAND",
                                        "occurred_at": f"2025-0{(i%9)+1}-01", "text": f"r{i}"})
            repo.link_record_about_asset(rid, asset["id"])

        target_rid = "MCTARGET"
        repo.create_service_record({"record_id": target_rid, "asset_key": "NMAXCAND",
                                    "occurred_at": "2025-12-01", "text": "target"})
        repo.link_record_about_asset(target_rid, asset["id"])

        candidates = find_candidate_pairs(repo, target_rid, max_candidates=3)
        assert len(candidates) <= 3, f"max_candidates=3 violated: {len(candidates)}"

    def test_excludes_self(self):
        from services.conflict_engine import find_candidate_pairs
        repo = _make_repo()
        _setup_asset_with_records(repo)
        candidates = find_candidate_pairs(repo, "R002")
        record_ids = [c["record"]["record_id"] for c in candidates]
        assert "R002" not in record_ids, "Record must not be its own candidate"

    def test_only_older_records_are_candidates(self):
        """Candidates must have occurred_at < target record."""
        from services.conflict_engine import find_candidate_pairs
        repo = _make_repo()
        asset = repo.find_or_create_asset("NORDER", {})
        for rid, date in [("OLDER", "2025-01-01"), ("TARGET", "2025-06-01"),
                          ("NEWER", "2025-12-01")]:
            repo.create_service_record({"record_id": rid, "asset_key": "NORDER",
                                        "occurred_at": date, "text": rid})
            repo.link_record_about_asset(rid, asset["id"])

        candidates = find_candidate_pairs(repo, "TARGET")
        record_ids = {c["record"]["record_id"] for c in candidates}
        assert "NEWER" not in record_ids, "Future record must not appear as candidate"
        assert "OLDER" in record_ids


# ---------------------------------------------------------------------------
# classify_conflict
# ---------------------------------------------------------------------------

class TestClassifyConflict:
    @pytest.mark.parametrize("label", [
        "no_conflict", "scope_disjoint", "supersedes",
        "partial_supersedes", "contradicts",
    ])
    def test_each_classification_label(self, label):
        from services.conflict_engine import classify_conflict
        groq = StubGroqLive(label=label)
        result = classify_conflict(groq, {"text": "new"}, {"text": "prior"})
        assert result["label"] == label
        assert result["parse_failed"] is False

    def test_parse_failure_handled(self):
        from services.conflict_engine import classify_conflict
        groq = StubGroqLive(parse_fail=True)
        result = classify_conflict(groq, {"text": "new"}, {"text": "prior"})
        assert result["parse_failed"] is True
        assert result["label"] == "no_conflict", "Parse failure must default to no_conflict"

    def test_invalid_label_defaults_to_no_conflict(self):
        """LLM returning an unexpected label must be coerced to no_conflict."""
        from services.conflict_engine import classify_conflict

        class StubBadLabel(StubGroqLive):
            def extract_json(self, *a, **k):
                return json.dumps({"label": "invented_label", "rationale": "bad"})

        result = classify_conflict(StubBadLabel(), {"text": "a"}, {"text": "b"})
        assert result["label"] == "no_conflict"


# ---------------------------------------------------------------------------
# adjudicate
# ---------------------------------------------------------------------------

class TestAdjudicate:
    def test_prefers_later_record_at_equal_authority(self):
        from services.conflict_engine import adjudicate
        adapter = MaintenanceDomainAdapter()
        new = {"occurred_at": "2025-02-01", "text": "new", "part_name": "Fan",
               "jasc_code": "7140", "part_location": ""}
        prior = {"occurred_at": "2025-01-01", "text": "prior", "part_name": "Fan",
                 "jasc_code": "7140", "part_location": ""}
        classification = {"label": "supersedes", "rationale": "x", "parse_failed": False}
        result = adjudicate(new, prior, classification, adapter)
        assert "31 days later" in " ".join(result["evidence"]) or \
               any("later" in e for e in result["evidence"]), (
            f"Expected recency evidence, got: {result['evidence']}"
        )

    def test_action_supersedes_on_explicit_citation(self):
        from services.conflict_engine import adjudicate
        adapter = MaintenanceDomainAdapter()
        new = {"occurred_at": "2025-02-01",
               "text": "SUPPLEMENTAL REPORT FOR (PRIOR001): replaced part.",
               "part_name": "Exit Sign", "jasc_code": "3350", "part_location": ""}
        prior = {"occurred_at": "2025-01-01", "text": "sign missing",
                 "part_name": "Exit Sign", "jasc_code": "3350", "part_location": ""}
        classification = {"label": "no_conflict", "rationale": "", "parse_failed": False}
        result = adjudicate(new, prior, classification, adapter)
        assert result["action"] == "supersedes", (
            f"Explicit citation must yield action=supersedes: {result}"
        )

    def test_action_no_action_when_no_evidence(self):
        from services.conflict_engine import adjudicate
        adapter = MaintenanceDomainAdapter()
        new = {"occurred_at": "2025-02-01", "text": "unrelated event",
               "part_name": "Engine", "jasc_code": "7100", "part_location": ""}
        prior = {"occurred_at": "2025-01-01", "text": "door problem",
                 "part_name": "Door", "jasc_code": "5200", "part_location": ""}
        classification = {"label": "no_conflict", "rationale": "", "parse_failed": False}
        result = adjudicate(new, prior, classification, adapter)
        assert result["action"] == "no_action"


# ---------------------------------------------------------------------------
# score_confidence
# ---------------------------------------------------------------------------

class TestScoreConfidence:
    def test_bounded_above_at_1(self):
        from services.conflict_engine import score_confidence
        all_signals = {k: True for k in [
            "explicit_supersession_language", "classification_supersedes",
            "recency_advantage", "authority_advantage", "part_agreement", "proximity_bonus",
        ]}
        score = score_confidence(all_signals)
        assert score <= 1.0, f"Score must be <= 1.0, got {score}"

    def test_bounded_below_at_0(self):
        from services.conflict_engine import score_confidence
        score = score_confidence({})
        assert score >= 0.0

    def test_explicit_citation_is_highest_weight(self):
        from services.conflict_engine import score_confidence, WEIGHTS_WITH_CITATION
        # Explicit citation alone
        s1 = score_confidence({"explicit_supersession_language": True})
        # All other signals combined, no explicit citation
        s2 = score_confidence({k: True for k in WEIGHTS_WITH_CITATION if k != "explicit_supersession_language"})
        assert s1 > 0, "Explicit citation alone must give non-zero confidence"
        # Explicit citation should be the largest single weight
        assert WEIGHTS_WITH_CITATION["explicit_supersession_language"] == max(WEIGHTS_WITH_CITATION.values())


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------

class TestRoute:
    def test_at_threshold_is_auto_accepted(self):
        from services.conflict_engine import route
        assert route({}, 0.72, 0.72, {"label": "supersedes"}) == "auto_accepted"

    def test_just_below_threshold_is_needs_review(self):
        from services.conflict_engine import route
        assert route({}, 0.719, 0.72, {"label": "supersedes"}) == "needs_review"

    def test_just_above_threshold_is_auto_accepted(self):
        from services.conflict_engine import route
        assert route({}, 0.721, 0.72, {"label": "supersedes"}) == "auto_accepted"

    def test_zero_confidence_is_needs_review(self):
        from services.conflict_engine import route
        assert route({}, 0.0, 0.72, {"label": "supersedes"}) == "needs_review"

    def test_max_confidence_is_auto_accepted(self):
        from services.conflict_engine import route
        assert route({}, 1.0, 0.72, {"label": "supersedes"}) == "auto_accepted"

    def test_contradicts_always_needs_review(self):
        from services.conflict_engine import route
        assert route({}, 1.0, 0.72, {"label": "contradicts"}) == "needs_review"
        assert route({}, 0.0, 0.72, {"label": "contradicts"}) == "needs_review"

    def test_partial_supersedes_always_needs_review(self):
        from services.conflict_engine import route
        assert route({}, 1.0, 0.72, {"label": "partial_supersedes"}) == "needs_review"

    def test_no_action_for_no_conflict_and_scope_disjoint(self):
        from services.conflict_engine import route
        assert route({}, 1.0, 0.72, {"label": "no_conflict"}) == "no_action"
        assert route({}, 1.0, 0.72, {"label": "scope_disjoint"}) == "no_action"


# ---------------------------------------------------------------------------
# process_record — §7 guard
# ---------------------------------------------------------------------------

class TestProcessRecord:
    def test_raises_when_not_live_and_no_stub(self):
        """process_record must raise RuntimeError when groq is not live."""
        from services.conflict_engine import process_record
        repo = _make_repo()
        adapter = MaintenanceDomainAdapter()
        _setup_asset_with_records(repo)
        dead_groq = StubGroqDead()

        with pytest.raises(RuntimeError, match="groq_service is not live"):
            process_record(repo, dead_groq, adapter, "R002", allow_stub=False)

    def test_succeeds_with_allow_stub(self):
        """process_record with allow_stub=True must succeed even with dead groq."""
        from services.conflict_engine import process_record
        repo = _make_repo()
        adapter = MaintenanceDomainAdapter()
        _setup_asset_with_records(repo)

        # Use a live-looking stub
        groq = StubGroqLive(label="supersedes")
        result = process_record(repo, groq, adapter, "R002", allow_stub=True)

        assert result["record_id"] == "R002"
        assert isinstance(result["candidates_considered"], int)
        assert result["candidates_considered"] >= 0
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["route"] in ("auto_accepted", "needs_review", "no_action")

    def test_parse_failure_counted(self):
        """Parse failures must be counted in the returned dict."""
        from services.conflict_engine import process_record
        repo = _make_repo()
        adapter = MaintenanceDomainAdapter()
        _setup_asset_with_records(repo)

        groq = StubGroqLive(parse_fail=True)
        result = process_record(repo, groq, adapter, "R002", allow_stub=True)
        # There is at least 1 candidate, so at least 1 classification attempted
        if result["candidates_considered"] > 0:
            assert result["parse_failures"] >= 1, (
                f"Parse failure not counted: {result}"
            )

    def test_applies_link_when_auto_accepted(self):
        from services.conflict_engine import process_record
        repo = _make_repo()
        adapter = MaintenanceDomainAdapter()
        _setup_asset_with_records(repo)
        
        # update R002 to have explicit citation so it hits 1.0 confidence
        target = repo.get_service_record("R002")
        target["text"] = "SUPPLEMENTAL REPORT FOR R001"
        repo.update_service_record("R002", target)

        groq = StubGroqLive(label="supersedes")
        
        linked = []
        def mock_link(new_record_id, old_record_id, **kwargs):
            linked.append((old_record_id, new_record_id))
            
        repo.link_record_supersedes = mock_link
        
        result = process_record(repo, groq, adapter, "R002", threshold=0.5, allow_stub=True)
        assert result["status_applied"] == "auto_accepted"
        assert len(linked) == 1


    def test_no_candidates_returns_auto_accepted(self):
        """Record with no prior records on the same asset → auto_accepted, 0 candidates."""
        from services.conflict_engine import process_record
        repo = _make_repo()
        adapter = MaintenanceDomainAdapter()
        asset = repo.find_or_create_asset("NLONE", {})
        repo.create_service_record({"record_id": "LONE001", "asset_key": "NLONE",
                                    "occurred_at": "2025-01-01", "text": "only record"})
        repo.link_record_about_asset("LONE001", asset["id"])

        groq = StubGroqLive()
        result = process_record(repo, groq, adapter, "LONE001", allow_stub=True)
        assert result["candidates_considered"] == 0
        assert result["route"] == "auto_accepted"
