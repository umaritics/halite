from graph.memory import MemoryGraphStore
from graph.repo import GraphRepository
from integrity.backfill import backfill_proposed_priors


def _repo():
    repo = GraphRepository(MemoryGraphStore())
    asset = repo.find_or_create_asset("N1")
    rows = {
        "OLD": {"submitted_at": "2025-01-01T09:00:00+00:00", "occurred_at": "2025-01-01", "analysis_state": "scored"},
        "A": {"submitted_at": "2025-02-01T09:00:00+00:00", "occurred_at": "2025-02-01", "analysis_state": "scored"},
        "B": {"submitted_at": "2025-03-01T09:00:00+00:00", "occurred_at": "2025-03-01",
              "analysis_state": "reviewed", "status": "accepted"},
        "HAS": {"submitted_at": "2025-04-01T09:00:00+00:00", "occurred_at": "2025-04-01",
                "analysis_state": "scored", "proposed_prior_id": "OLD"},
        "RAW": {"submitted_at": "2025-05-01T09:00:00+00:00", "occurred_at": "2025-05-01"},
    }
    for rid, extra in rows.items():
        repo.create_service_record({
            "record_id": rid, "asset_key": "N1", "part_name": "Pump", "text": "t",
            "submitted_at": extra.pop("submitted_at"), "occurred_at": extra.pop("occurred_at"),
        })
        repo.update_service_record(rid, extra)
        repo.link_record_about_asset(rid, asset["id"])
    return repo


def test_a_dry_run_counts_and_changes_nothing():
    repo = _repo()
    counts = backfill_proposed_priors(repo, dry_run=True)
    # OLD has no earlier report, A can point at OLD, B is reviewed, HAS already has one, RAW is unanalysed.
    assert counts == {"examined": 3, "would_set": 1, "no_prior_found": 1, "skipped_reviewed": 1}
    assert all(repo.get_service_record(r).get("proposed_prior_id") is None for r in ("OLD", "A", "B", "RAW"))


def test_the_real_run_sets_the_field_and_skips_a_reviewed_record():
    repo = _repo()
    assert backfill_proposed_priors(repo, dry_run=False) == {
        "examined": 3, "would_set": 1, "no_prior_found": 1, "skipped_reviewed": 1,
    }
    assert repo.get_service_record("A")["proposed_prior_id"] == "OLD"
    assert repo.get_service_record("B").get("proposed_prior_id") is None
    assert repo.get_service_record("HAS")["proposed_prior_id"] == "OLD"
    assert backfill_proposed_priors(repo, dry_run=False)["would_set"] == 0
