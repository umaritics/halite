"""Regression tests for the legacy placeholder migration."""

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from scripts.migrate_conflict_analysis_state import migrate


def _repo():
    return GraphRepository(MemoryGraphStore())


def _seed(repo, record_id, **overrides):
    data = {
        "record_id": record_id,
        "asset_key": "NTEST",
        "occurred_at": "2025-01-01",
        "text": "test",
        "status": "auto_accepted",
        "confidence": 1.0,
    }
    data.update(overrides)
    return repo.create_service_record(data)


def test_dry_run_does_not_mutate_and_apply_is_idempotent():
    repo = _repo()
    _seed(repo, "LEGACY1", analysis_state=None)

    dry = migrate(repo)
    assert dry["mode"] == "dry_run"
    assert dry["would_change"] == 1
    assert repo.get_service_record("LEGACY1")["confidence"] == 1.0

    applied = migrate(repo, apply=True)
    assert applied["changed"] == 1
    record = repo.get_service_record("LEGACY1")
    assert record["confidence"] is None
    assert record["legacy_confidence"] == 1.0
    assert record["analysis_state"] == "unscored"
    assert migrate(repo, apply=True)["changed"] == 0


def test_genuinely_scored_record_is_never_reset():
    repo = _repo()
    _seed(
        repo,
        "SCORED1",
        analysis_state="scored",
        scored_at="2025-01-02T00:00:00Z",
        classification_label="supersedes",
    )

    assert migrate(repo, apply=True)["changed"] == 0
    assert repo.get_service_record("SCORED1")["confidence"] == 1.0


def test_restore_uses_legacy_confidence_only_if_still_unscored():
    repo = _repo()
    _seed(repo, "RESTORE1", analysis_state=None)
    migrate(repo, apply=True)

    restored = migrate(repo, restore=True)
    assert restored["changed"] == 1
    record = repo.get_service_record("RESTORE1")
    assert record["confidence"] == 1.0
    assert record["status"] == "auto_accepted"
    assert record["legacy_confidence"] is None

    migrate(repo, apply=True)
    repo.update_service_record("RESTORE1", {
        "analysis_state": "scored", "confidence": 0.8, "scored_at": "now"
    })
    assert migrate(repo, restore=True)["changed"] == 0
    assert repo.get_service_record("RESTORE1")["confidence"] == 0.8
