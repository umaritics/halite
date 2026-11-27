"""Unit tests for graph-only benchmark ranker B4."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.rank_b4 import rank_parts_graph


@pytest.fixture()
def corpus() -> pd.DataFrame:
    rows = [
        dict(
            OperatorControlNumber="R1",
            SubmissionDate="01/01/2025 10:00:00",
            RegistryNNumber="NT1",
            AircraftMake="BOEING",
            AircraftModel="737",
            PartName="VALVE",
            _submitted_dt=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        dict(
            OperatorControlNumber="R2",
            SubmissionDate="01/03/2025 10:00:00",
            RegistryNNumber="NT1",
            AircraftMake="BOEING",
            AircraftModel="737",
            PartName="PUMP",
            _submitted_dt=datetime(2025, 1, 3, tzinfo=timezone.utc),
        ),
        dict(
            OperatorControlNumber="R3",
            SubmissionDate="01/02/2025 10:00:00",
            RegistryNNumber="NT2",
            AircraftMake="BOEING",
            AircraftModel="737",
            PartName="VALVE",
            _submitted_dt=datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        dict(
            OperatorControlNumber="R4",
            SubmissionDate="01/02/2025 10:00:00",
            RegistryNNumber="NT9",
            AircraftMake="AIRBUS",
            AircraftModel="A320",
            PartName="DOOR",
            _submitted_dt=datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
    ]
    return pd.DataFrame(rows)


def test_graph_ranker_prefers_own_aircraft_then_model(corpus):
    ranked = rank_parts_graph(
        corpus,
        "NT1",
        datetime(2025, 1, 4, tzinfo=timezone.utc),
        query_model_key="BOEING|737",
    )
    parts = [r["part_name"] for r in ranked]
    assert set(parts) == {"PUMP", "VALVE"}
    assert "DOOR" not in parts
    pump = next(r for r in ranked if r["part_name"] == "PUMP")
    assert "same_aircraft" in pump["sources"]
    assert any("same_model" in r.get("sources", []) for r in ranked)