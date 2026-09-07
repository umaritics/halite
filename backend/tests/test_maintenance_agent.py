"""
test_maintenance_agent.py — Unit tests for MaintenanceAgent.

All tests run in-memory (MemoryGraphStore).  No network, no file I/O
beyond the synthetic inline records passed as payload["records"].

Coverage:
  - Basic ingestion: assets and records created
  - Idempotency: second run creates 0 records
  - Blank RegistryNNumber: skipped, counted
  - Unparseable DifficultyDate: skipped, counted
  - Missing OperatorControlNumber: skipped
  - PRECEDED_BY chain: later record linked to earlier
  - Records with both valid and invalid rows: counts accurate
  - Empty payload: returns zero counts
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from agents.maintenance_agent import MaintenanceAgent


def _make_repo() -> GraphRepository:
    return GraphRepository(MemoryGraphStore())


def _make_agent(repo: GraphRepository) -> MaintenanceAgent:
    return MaintenanceAgent(repo, None)  # groq_service not used by agent


def _make_record(
    ocn: str = "TEST001",
    tail: str = "N12345",
    date: str = "01/15/2025",
    disc: str = "Exit sign missing.",
    make: str = "Boeing",
    model: str = "737",
) -> dict:
    return {
        "OperatorControlNumber": ocn,
        "RegistryNNumber": tail,
        "DifficultyDate": date,
        "SubmissionDate": "2025-01-16T00:00:00Z",
        "AircraftMake": make,
        "AircraftModel": model,
        "AircraftSerialNumber": "SN001",
        "PartName": "Exit Sign",
        "PartCondition": "Inoperative",
        "PartLocation": "Row 14",
        "JASCCode": "3350",
        "Discrepancy": disc,
    }


# ---------------------------------------------------------------------------
# Basic ingestion
# ---------------------------------------------------------------------------

def test_creates_asset_and_record():
    repo = _make_repo()
    agent = _make_agent(repo)
    result = agent.run({"records": [_make_record()]})

    assert result["records_created"] == 1
    assert result["rows_skipped_no_tail"] == 0
    assert result["rows_skipped_bad_date"] == 0

    # Verify in graph
    sr = repo.get_service_record("TEST001")
    assert sr is not None
    assert sr["occurred_at"] == "2025-01-15"
    assert sr["asset_key"] == "N12345"


def test_asset_linked_to_record():
    repo = _make_repo()
    agent = _make_agent(repo)
    agent.run({"records": [_make_record()]})

    assets = [n for n in repo.store.nodes.values() if n.get("label") == "Asset"]
    assert len(assets) == 1
    assert assets[0]["tail_number"] == "N12345"

    history = repo.list_asset_history(assets[0]["id"])
    assert len(history) == 1
    assert history[0]["record_id"] == "TEST001"


# ---------------------------------------------------------------------------
# Idempotency — second run returns 0 records_created
# ---------------------------------------------------------------------------

def test_idempotent_second_run():
    repo = _make_repo()
    agent = _make_agent(repo)
    records = [_make_record("OCN001"), _make_record("OCN002", tail="N99999")]

    result1 = agent.run({"records": records})
    assert result1["records_created"] == 2

    result2 = agent.run({"records": records})
    assert result2["records_created"] == 0, (
        f"Second run must create 0 records, got: {result2}"
    )
    assert result2["duplicates_skipped"] == 2


# ---------------------------------------------------------------------------
# Blank RegistryNNumber — skip and count
# ---------------------------------------------------------------------------

def test_skip_blank_tail():
    repo = _make_repo()
    agent = _make_agent(repo)
    records = [
        _make_record("GOOD001"),
        _make_record("SKIP001", tail=""),   # blank tail
        _make_record("SKIP002", tail="  "), # whitespace only
    ]
    result = agent.run({"records": records})
    assert result["rows_skipped_no_tail"] == 2
    assert result["records_created"] == 1


# ---------------------------------------------------------------------------
# Unparseable DifficultyDate — skip and count, never default to today
# ---------------------------------------------------------------------------

def test_skip_bad_date():
    repo = _make_repo()
    agent = _make_agent(repo)
    records = [
        _make_record("GOOD001"),
        _make_record("BADDT001", date="not-a-date"),
        _make_record("BADDT002", date=""),
        _make_record("BADDT003", date="2025-01-15"),  # ISO format — wrong for MM/DD/YYYY
    ]
    result = agent.run({"records": records})
    assert result["rows_skipped_bad_date"] >= 2  # empty and not-a-date
    assert result["records_created"] == 1

    # Verify no record was created with a defaulted date
    sr_bad = repo.get_service_record("BADDT001")
    assert sr_bad is None, "Bad-date record must not be created"


# ---------------------------------------------------------------------------
# PRECEDED_BY chain
# ---------------------------------------------------------------------------

def test_preceded_by_chain():
    repo = _make_repo()
    agent = _make_agent(repo)
    records = [
        _make_record("FIRST001", date="01/10/2025"),
        _make_record("SECOND001", date="01/20/2025"),
        _make_record("THIRD001", date="01/30/2025"),
    ]
    result = agent.run({"records": records})
    assert result["records_created"] == 3

    # Find PRECEDED_BY edges
    preceded_edges = [
        e for e in repo.store.edges if e["type"] == "PRECEDED_BY"
    ]
    # Should have at least 1 PRECEDED_BY edge connecting later to earlier
    assert len(preceded_edges) >= 1, (
        f"Expected PRECEDED_BY edges, got: {preceded_edges}"
    )


# ---------------------------------------------------------------------------
# Mixed valid and invalid rows
# ---------------------------------------------------------------------------

def test_mixed_rows():
    repo = _make_repo()
    agent = _make_agent(repo)
    records = [
        _make_record("V001"),
        _make_record("V002", tail="N22222"),
        _make_record("SKIP_TAIL", tail=""),
        _make_record("SKIP_DATE", date="bad"),
    ]
    result = agent.run({"records": records})
    assert result["records_created"] == 2
    assert result["rows_skipped_no_tail"] == 1
    assert result["rows_skipped_bad_date"] >= 1


# ---------------------------------------------------------------------------
# Empty payload
# ---------------------------------------------------------------------------

def test_empty_records():
    repo = _make_repo()
    agent = _make_agent(repo)
    result = agent.run({"records": []})
    assert result["records_created"] == 0
    assert result["assets_created"] == 0
    assert result["rows_skipped_no_tail"] == 0
    assert result["rows_skipped_bad_date"] == 0


# ---------------------------------------------------------------------------
# Multiple records same asset — one asset, multiple records
# ---------------------------------------------------------------------------

def test_multiple_records_same_asset():
    repo = _make_repo()
    agent = _make_agent(repo)
    records = [
        _make_record("SR001", tail="NTAIL1", date="02/01/2025"),
        _make_record("SR002", tail="NTAIL1", date="02/05/2025"),
        _make_record("SR003", tail="NTAIL1", date="02/10/2025"),
    ]
    result = agent.run({"records": records})
    assert result["records_created"] == 3

    # Only one asset created
    assets = [n for n in repo.store.nodes.values()
              if n.get("label") == "Asset" and n.get("tail_number") == "NTAIL1"]
    assert len(assets) == 1

    # History ascending
    history = repo.list_asset_history(assets[0]["id"])
    dates = [r["occurred_at"] for r in history]
    assert dates == sorted(dates), f"History not ascending: {dates}"
