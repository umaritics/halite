"""Route-level tests for the stateless diagnostic copilot."""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from services.groq_service import GroqService
from tests.conftest import _build_test_app


class FakeCopilotLlm:
    demo_mode = False
    model = "fake-copilot"
    fallback_invocations = 0

    def __init__(self, reply="Evidence from SWIA2024010100001."):
        self.reply = reply

    @property
    def is_live(self):
        return True

    def chat(self, messages, **kwargs):
        prompt = messages[-1]["content"]
        if prompt.startswith("Extract NEW maintenance case facts"):
            message = prompt.split("MESSAGE:", 1)[-1].lower()
            facts = {
                "symptoms": ["crack drag angle"] if "crack" in message else [],
                "observations": ["hydraulic pump leak"] if "hydraulic" in message else [],
                "checks_done": ["visual inspection"] if "inspection done" in message else [],
                "ruled_out": ["PUMP"] if "rule out" in message else [],
                "open_questions": [],
            }
            return json.dumps(facts)
        return self.reply


class DeadLlm:
    demo_mode = True
    model = "dead"
    fallback_invocations = 0

    @property
    def is_live(self):
        return False


class EmptyReplyLlm(FakeCopilotLlm):
    def chat(self, messages, **kwargs):
        prompt = messages[-1]["content"]
        if prompt.startswith("Extract NEW maintenance case facts"):
            return super().chat(messages, **kwargs)
        return ""


class EmptyDiagnoseLlm(FakeCopilotLlm):
    def chat(self, *args, **kwargs):
        return json.dumps({"explanation": "", "rare_cases": [], "warnings": []})


def seed_case(app):
    repo = app.state.graph_repo
    target = repo.find_or_create_asset("N813SK", {})
    fleet = repo.find_or_create_asset("N900ZZ", {})
    records = [
        ("SWIA2024010100001", target, "2024-01-01", "DRAG ANGLE", "crack at drag angle", "auto_accepted"),
        ("SWIA2024020200002", target, "2024-02-02", "PUMP", "routine pump inspection", "auto_accepted"),
        ("SWIA2023030300003", target, "2023-03-03", "SEAL", "old seal instruction", "superseded"),
        ("AALA2024050500004", fleet, "2024-05-05", "PUMP", "hydraulic pump leak and pressure loss", "auto_accepted"),
        ("AALA2022060600005", fleet, "2022-06-06", "DRAG ANGLE", "drag angle crack found", "auto_accepted"),
    ]
    for record_id, asset, occurred_at, part_name, text, status in records:
        repo.create_service_record({
            "record_id": record_id,
            "asset_key": asset["tail_number"],
            "occurred_at": occurred_at,
            "part_name": part_name,
            "text": text,
            "status": status,
        })
        repo.link_record_about_asset(record_id, asset["id"])
    return target["id"]


def make_client(llm=None):
    app = _build_test_app()
    app.state.groq_service = llm or FakeCopilotLlm()
    asset_id = seed_case(app)
    return app, asset_id


def post_turn(app, payload):
    with TestClient(app) as client:
        return client.post("/api/maintenance/copilot/turn", json=payload)


def test_second_turn_reranks_accumulated_case_and_reports_delta():
    app, asset_id = make_client()
    first = post_turn(app, {"asset_id": asset_id, "message": "crack found on drag angle"}).json()
    second = post_turn(app, {
        "session_id": first["session_id"],
        "asset_id": asset_id,
        "message": "hydraulic pump leak observed",
        "case_state": first["case_state"],
    }).json()
    assert second["case_state"]["symptoms"] == ["crack drag angle"]
    assert second["case_state"]["observations"] == ["hydraulic pump leak"]
    assert first["ranked_checks"] != second["ranked_checks"]
    assert any(second["ranking_delta"][key] for key in ("moved_up", "moved_down", "new"))


def test_ruled_out_component_is_not_recommended():
    app, asset_id = make_client()
    response = post_turn(app, {
        "asset_id": asset_id,
        "message": "rule out pump",
        "case_state": {"symptoms": ["hydraulic pump leak"]},
    })
    assert response.status_code == 200
    assert "PUMP" not in [item["part_name"] for item in response.json()["ranked_checks"]]


def test_invalid_citation_is_flagged_and_never_verified():
    llm = FakeCopilotLlm("Compare SWIA2024010100001 with FAKE2024999999999.")
    app, asset_id = make_client(llm)
    data = post_turn(app, {"asset_id": asset_id, "message": "crack found"}).json()
    assert data["citation_validation"]["valid_ids"] == ["SWIA2024010100001"]
    assert data["citation_validation"]["invalid_ids"] == ["FAKE2024999999999"]
    assert "[UNVERIFIED:FAKE2024999999999]" in data["reply"]


def test_superseded_record_is_marked_but_not_used_in_ranked_recommendations():
    app, asset_id = make_client()
    data = post_turn(app, {"asset_id": asset_id, "message": "crack found"}).json()
    old = next(item for item in data["evidence"] if item["record_id"] == "SWIA2023030300003")
    assert old["is_superseded"] is True
    assert all(
        "SWIA2023030300003" not in item["evidence_record_ids"]
        for item in data["ranked_checks"]
    )


def test_validation_unknown_asset_and_model_failure_states():
    app, _ = make_client()
    assert post_turn(app, {"asset_id": "missing", "message": "noise"}).status_code == 404
    assert post_turn(app, {"message": "   "}).status_code == 422
    assert post_turn(app, {"message": "x" * 4001}).status_code == 422

    app.state.groq_service = DeadLlm()
    unavailable = post_turn(app, {"message": "hydraulic pump leak"})
    assert unavailable.status_code == 200
    body = unavailable.json()
    assert body["llm_status"] == "unavailable"
    assert body["reply"] is None
    assert body["ranked_checks"]

    app.state.groq_service = EmptyReplyLlm()
    empty = post_turn(app, {"message": "crack found"}).json()
    assert empty["llm_status"] == "unavailable"
    assert empty["reply"] is None
    assert any("empty" in warning.lower() for warning in empty["warnings"])


def test_fleet_only_mode_and_deterministic_record_report_selection():
    llm = FakeCopilotLlm("Records state: SWIA2024010100001. Interpretation: root cause is not in the data.")
    app, _ = make_client(llm)
    fleet = post_turn(app, {"message": "crack found on drag angle"})
    assert fleet.status_code == 200
    assert fleet.json()["ranked_checks"]

    report = post_turn(app, {"message": "summarize record SWIA2024010100001"}).json()
    assert [item["record_id"] for item in report["evidence"]][:1] == ["SWIA2024010100001"]


def test_period_and_topic_report_selects_only_matching_asset_records():
    llm = FakeCopilotLlm("Records state: SWIA2024020200002.")
    app, asset_id = make_client(llm)
    data = post_turn(app, {
        "asset_id": asset_id,
        "message": "summarize this aircraft's pump history for 2024",
    }).json()
    assert data["evidence"][0]["record_id"] == "SWIA2024020200002"


def test_diagnose_empty_explanation_regression_is_explicit_503():
    app, asset_id = make_client(EmptyDiagnoseLlm())
    with TestClient(app) as client:
        response = client.post(
            "/api/maintenance/diagnose",
            json={"asset_id": asset_id, "symptom_text": "crack found"},
        )
    assert response.status_code == 503
    assert "empty explanation" in response.json()["detail"].lower()


def test_groq_wrapper_rejects_none_content_with_finish_reason():
    service = GroqService("fake-key", model="openai/gpt-oss-20b")
    service.demo_mode = False
    completion = SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=None),
            finish_reason="length",
        )]
    )
    service.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: completion)
        )
    )
    with pytest.raises(RuntimeError, match="empty model response"):
        service.chat([{"role": "user", "content": "test"}])
