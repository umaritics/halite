"""U4/U5 API tests for POST /api/maintenance/diagnose LLM boundary + citations."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from tests.conftest import _build_test_app


class _DeadGroq:
    demo_mode = True
    model = "dead-model"
    fallback_invocations = 0

    @property
    def is_live(self) -> bool:
        return False

    def chat(self, *args, **kwargs):
        raise AssertionError("chat must not be called when is_live is False")


class _LiveGroq:
    demo_mode = False
    model = "live-stub-model"
    fallback_invocations = 0

    def __init__(self, explanation: str):
        self._explanation = explanation

    @property
    def is_live(self) -> bool:
        return True

    def chat(self, *args, **kwargs) -> str:
        return json.dumps({
            "explanation": self._explanation,
            "rare_cases": [],
            "warnings": [],
        })


def _seed_faa_asset(app):
    repo = app.state.graph_repo
    asset = repo.find_or_create_asset("N813SK", {"make": "Airbus", "model": "A321"})
    repo.create_service_record({
        "record_id": "SWIA2025091876593",
        "asset_key": "N813SK",
        "occurred_at": "2025-09-18",
        "part_name": "PUMP",
        "jasc_code": "2900",
        "text": "Hydraulic pump leak at seal",
        "status": "auto_accepted",
        "confidence": 0.9,
    })
    repo.link_record_about_asset("SWIA2025091876593", asset["id"])
    repo.create_service_record({
        "record_id": "AALA202504075792",
        "asset_key": "N813SK",
        "occurred_at": "2025-04-07",
        "part_name": "SEAL",
        "jasc_code": "2900",
        "text": "Replaced pump seal after leak",
        "status": "auto_accepted",
        "confidence": 0.85,
    })
    repo.link_record_about_asset("AALA202504075792", asset["id"])
    return asset["id"]


class TestDiagnoseLlmBoundary:
    def test_503_when_llm_not_live(self):
        app = _build_test_app()
        app.state.groq_service = _DeadGroq()
        asset_id = _seed_faa_asset(app)
        with TestClient(app) as client:
            resp = client.post(
                "/api/maintenance/diagnose",
                json={"asset_id": asset_id, "symptom_text": "pump leak"},
            )
        assert resp.status_code == 503
        assert "Groq" in resp.json()["detail"]

    def test_404_when_no_history(self):
        app = _build_test_app()
        app.state.groq_service = _LiveGroq("no citations")
        with TestClient(app) as client:
            resp = client.post(
                "/api/maintenance/diagnose",
                json={
                    "asset_id": "00000000-0000-0000-0000-000000000000",
                    "symptom_text": "noise",
                },
            )
        assert resp.status_code == 404


class TestDiagnoseCitations:
    def test_flags_invented_ids_keeps_real(self):
        app = _build_test_app()
        asset_id = _seed_faa_asset(app)
        app.state.groq_service = _LiveGroq(
            "Inspect using SWIA2025091876593; ignore FAKE2025999999999."
        )
        with TestClient(app) as client:
            resp = client.post(
                "/api/maintenance/diagnose",
                json={"asset_id": asset_id, "symptom_text": "hydraulic pump leak"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["citation_validation"]["all_valid"] is False
        assert "SWIA2025091876593" in data["citation_validation"]["valid_ids"]
        assert "FAKE2025999999999" in data["citation_validation"]["invalid_ids"]
        assert "[UNVERIFIED:FAKE2025999999999]" in data["explanation"]
        assert data["ranked_checks"]
        assert data["ranked_checks"][0]["part_name"]

    def test_all_valid_when_only_graph_ids(self):
        app = _build_test_app()
        asset_id = _seed_faa_asset(app)
        app.state.groq_service = _LiveGroq(
            "Evidence from SWIA2025091876593 and AALA202504075792."
        )
        with TestClient(app) as client:
            resp = client.post(
                "/api/maintenance/diagnose",
                json={"asset_id": asset_id, "symptom_text": "pump seal"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["citation_validation"]["all_valid"] is True
        assert data["citation_validation"]["invalid_ids"] == []
