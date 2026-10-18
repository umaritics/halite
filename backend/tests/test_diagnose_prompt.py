"""Regression: /diagnose must send the model a real prompt.

A merge once left ``_build_prompt`` without its body, so it returned ``None`` and a live model
rejected every request (HTTP 400, surfaced as 503). The older tests used a fake model that ignored
its input, so they passed anyway. These tests inspect what the model is actually sent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from api.routes.diagnostics import _build_prompt
from services.diagnostic_retrieval import build_diagnostic_context, rank_diagnostic_checks
from tests.conftest import _build_test_app
from tests.test_api_diagnostics import _seed_faa_asset


class _RecordingGroq:
    """A live-looking model that records exactly what it is sent and refuses a null prompt."""
    demo_mode = False
    model = "recording-model"
    fallback_invocations = 0

    def __init__(self):
        self.calls = []

    @property
    def is_live(self) -> bool:
        return True

    def chat(self, messages, system_prompt=None, **_):
        for m in messages:
            # Groq answers HTTP 400 when a user message has no string content.
            assert isinstance(m.get("content"), str) and m["content"].strip(), "model was sent an empty prompt"
        self.calls.append(messages)
        return json.dumps({"explanation": "See SWIA2025091876593.", "rare_cases": [], "warnings": []})


def test_build_prompt_returns_a_complete_prompt():
    app = _build_test_app()
    asset_id = _seed_faa_asset(app)
    ctx = build_diagnostic_context(app.state.graph_repo, asset_id, "hydraulic pump leak")
    ranked = rank_diagnostic_checks(ctx)

    prompt = _build_prompt(ctx, ranked)

    assert isinstance(prompt, str) and len(prompt) > 200
    assert "hydraulic pump leak" in prompt          # the symptom
    assert asset_id in prompt                        # the aircraft
    assert ranked[0]["part_name"] in prompt          # the pre-ranked component
    assert "SWIA2025091876593" in prompt             # a real record id the model may cite
    assert "Do NOT invent record IDs" in prompt      # the citation rule
    assert '"explanation"' in prompt                 # the required JSON shape


def test_diagnose_sends_the_prompt_to_the_model_and_returns_its_explanation():
    app = _build_test_app()
    asset_id = _seed_faa_asset(app)
    model = _RecordingGroq()
    app.state.groq_service = model

    with TestClient(app) as client:
        resp = client.post(
            "/api/maintenance/diagnose",
            json={"asset_id": asset_id, "symptom_text": "hydraulic pump leak"},
        )

    assert resp.status_code == 200
    assert len(model.calls) == 1
    sent = model.calls[0][0]["content"]
    assert "hydraulic pump leak" in sent and "SWIA2025091876593" in sent
    assert resp.json()["explanation"]
    assert resp.json()["citation_validation"]["all_valid"] is True
