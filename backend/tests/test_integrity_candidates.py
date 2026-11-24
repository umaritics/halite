import hashlib

import pytest

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from integrity.candidates import ORDERINGS, PAIR_WEIGHTS, pair_score, rank_candidates
from integrity.prompts import CLASSIFICATION_PROMPTS, system_prompt
from services.conflict_engine import PAIR_WEIGHTS as ENGINE_WEIGHTS, find_candidate_pairs

# Pins the prompt staging uses: captured from the engine before the prompt moved.
V1_SHA256 = "34439bb69d3e51ddfa28f61852a740c270b1bd3d3dc91470f86cd48c045508d8"


def rec(rid, submitted, text="x", part="PUMP", jasc="", loc="", occurred="2025-01-01"):
    return {
        "record_id": rid, "occurred_at": occurred, "submitted_at": submitted,
        "part_name": part, "jasc_code": jasc, "part_location": loc, "text": text,
    }


TARGET = rec("T", "2025-03-01T00:00:00+00:00", text="pump seal cracked leaking", jasc="1")
HISTORY = [
    rec("A", "2025-02-27T00:00:00+00:00", text="pump seal cracked leaking fluid", jasc="1"),
    rec("B", "2025-02-01T00:00:00+00:00", text="unrelated cabin light", occurred="2025-01-05"),
    rec("C", "2025-02-28T00:00:00+00:00", text="hydraulic pump seal", jasc="2", occurred="2025-01-03"),
    TARGET,
    rec("LATER", "2025-03-05T00:00:00+00:00", text="pump seal cracked leaking"),
    rec("ZERO", "2025-02-20T00:00:00+00:00", part="DOOR", occurred="2024-01-01"),
]


def ids(candidates):
    return [c["record"]["record_id"] for c in candidates]


def test_prompt_v1_is_pinned_to_the_staging_bytes():
    assert hashlib.sha256(system_prompt("v1").encode()).hexdigest() == V1_SHA256


def test_prompt_v2_differs_from_v1_only_in_two_definition_lines():
    v1 = system_prompt("v1").splitlines()
    v2 = system_prompt("v2-unannounced").splitlines()
    assert len(v1) == len(v2)
    changed = [line for old, line in zip(v1, v2) if old != line]
    assert len(changed) == 2
    assert changed[0].lstrip().startswith("supersedes")
    assert changed[1].lstrip().startswith("partial_supersedes")
    assert set(CLASSIFICATION_PROMPTS) == {"v1", "v2-unannounced"}


def test_unknown_prompt_version_raises():
    with pytest.raises(ValueError):
        system_prompt("v9")


def test_engine_keeps_pair_weights_name():
    assert ENGINE_WEIGHTS is PAIR_WEIGHTS


def test_pair_score_adds_the_four_checks():
    prior = rec("P", "2025-02-01T00:00:00+00:00", jasc="9", loc="L1", occurred="2025-01-10")
    target = rec("N", "2025-03-01T00:00:00+00:00", jasc="9", loc="L1")
    assert pair_score(target, prior) == sum(PAIR_WEIGHTS.values())
    assert pair_score(rec("N", "x", part="DOOR", occurred="2020-01-01"), prior) == 0


def test_legacy_orders_by_score_then_date_then_id_without_screen_features():
    result = rank_candidates(TARGET, HISTORY)
    # A shares the JASC code (score 6); B and C score 4 and B is the later occurrence.
    assert ids(result) == ["A", "B", "C"]
    assert [c["score"] for c in result] == [6, 4, 4]
    assert all("screen_features" not in c for c in result)


def test_legacy_breaks_full_ties_by_record_id():
    history = [rec("Z", "2025-02-01T00:00:00+00:00"), rec("M", "2025-02-02T00:00:00+00:00")]
    assert ids(rank_candidates(TARGET, history)) == ["M", "Z"]


def test_containment_puts_best_text_overlap_first_and_attaches_features():
    result = rank_candidates(TARGET, HISTORY, ordering="containment")
    assert ids(result) == ["A", "C", "B"]
    assert all("screen_features" in c for c in result)


def test_submission_gap_puts_nearest_submission_first_and_unknown_last():
    history = HISTORY + [rec("NOSUB", "", text="pump", occurred="2024-12-31")]
    result = rank_candidates(TARGET, history, ordering="submission_gap")
    assert ids(result) == ["C", "A", "B", "NOSUB"]
    assert all("screen_features" not in c for c in result)


def test_later_submitted_zero_score_and_rejected_priors_are_dropped():
    result = rank_candidates(TARGET, HISTORY)
    assert "LATER" not in ids(result)
    assert "ZERO" not in ids(result)
    assert "T" not in ids(result)
    assert "A" not in ids(rank_candidates(TARGET, HISTORY, rejected={"A"}))


def test_cap_is_respected_and_none_means_no_cap():
    assert len(rank_candidates(TARGET, HISTORY, max_candidates=2)) == 2
    assert len(rank_candidates(TARGET, HISTORY, max_candidates=None)) == 3


def test_unknown_ordering_raises():
    with pytest.raises(ValueError):
        rank_candidates(TARGET, HISTORY, ordering="nope")
    assert ORDERINGS == ("legacy", "containment", "submission_gap")


@pytest.mark.parametrize("mode,ordering", [("legacy", "legacy"), ("cascade", "containment")])
def test_find_candidate_pairs_matches_rank_candidates(mode, ordering):
    repo = GraphRepository(MemoryGraphStore())
    asset = repo.find_or_create_asset("NEQUIV", {})
    records = [
        rec("E1", "2025-01-02T10:00:00-05:00", text="hydraulic pump seal cracked", jasc="29", loc="L", occurred="2025-01-02"),
        rec("E2", "2025-01-09T10:00:00-05:00", text="routine pump inspection", jasc="29", occurred="2025-01-09"),
        rec("E3", "2025-01-15T10:00:00-05:00", text="pump seal cracked leaking", part="PUMP", occurred="2025-01-15"),
        rec("E4", "2025-02-20T10:00:00-05:00", text="valve", part="VALVE", occurred="2025-02-20"),
        rec("E5", "2025-03-01T10:00:00-05:00", text="SUPPLEMENTAL REPORT FOR (E1): pump seal cracked replaced", jasc="29", loc="L", occurred="2025-03-01"),
    ]
    for r in records:
        repo.create_service_record({"asset_key": "NEQUIV", "source": "faa_sdr", **r})
        repo.link_record_about_asset(r["record_id"], asset["id"])
    target = repo.get_service_record("E5")
    expected = rank_candidates(
        target, repo.list_asset_history(asset["id"], limit=200),
        ordering=ordering, rejected=repo.rejected_prior_ids("E5"), max_candidates=25,
    )
    actual = find_candidate_pairs(repo, "E5", analysis_mode=mode)
    assert ids(actual) == ids(expected)
    assert len(actual) >= 2
    assert all(("screen_features" in c) == (mode == "cascade") for c in actual)
