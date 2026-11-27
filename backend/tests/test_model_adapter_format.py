"""Provider-boundary tests: prose and structured extraction use distinct formats."""
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from services.groq_service import GroqService


@pytest.fixture
def local_provider(monkeypatch):
    requests = []
    original_client = httpx.Client

    def handle(request):
        import json
        requests.append(json.loads(request.content))
        content = "{}" if "response_format" in requests[-1] else "supported reply"
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        })

    def client(**kwargs):
        return original_client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(httpx, "Client", client)
    service = GroqService("test-key", model="test-model", provider="openai_compatible",
                          openai_compat_base_url="http://model.test/v1")
    return service, requests


@pytest.mark.parametrize("with_usage", [False, True])
def test_local_prose_omits_json_format_and_preserves_usage(local_provider, with_usage):
    service, requests = local_provider
    call = service.chat_with_usage if with_usage else service.chat
    result = call([{"role": "user", "content": "explain"}], "evidence only", 123)
    assert "response_format" not in requests[0]
    assert requests[0]["max_tokens"] == 123
    assert requests[0]["messages"][0] == {"role": "system", "content": "evidence only"}
    assert (result["content"] if with_usage else result) == "supported reply"
    if with_usage:
        assert result["usage"]["total_tokens"] == 6


@pytest.mark.parametrize("with_usage", [False, True])
def test_local_extraction_explicitly_requests_json(local_provider, with_usage):
    service, requests = local_provider
    call = service.extract_json_with_usage if with_usage else service.extract_json
    call("classify", "extract JSON", 321)
    assert requests[0]["response_format"] == {"type": "json_object"}
    assert requests[0]["max_tokens"] == 321


def test_local_explicit_chat_json_mode(local_provider):
    service, requests = local_provider
    service.chat([], json_mode=True)
    assert requests[0]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("json_mode", [False, True])
def test_groq_format_parity_and_retry_preserves_mode(monkeypatch, json_mode):
    import config
    monkeypatch.setattr(config.settings, "GROQ_API_KEY_FALLBACK", "fallback-test-key")
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))], usage=None,
    )
    create = Mock(side_effect=[RuntimeError("429 rate limit"), response])
    service = GroqService("", demo_mode=True)
    service.demo_mode = False
    service.api_key = "initial-test-key"
    service.client = SimpleNamespace(
        api_key=service.api_key, chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )
    assert service.chat([], json_mode=json_mode) == "ok"
    assert create.call_count == 2
    for call in create.call_args_list:
        if json_mode:
            assert call.kwargs["response_format"] == {"type": "json_object"}
        else:
            assert "response_format" not in call.kwargs
    assert service.client.api_key == "fallback-test-key"


def test_copilot_fact_extraction_uses_structured_local_output(local_provider):
    from api.routes.diagnostics import _extract_case_facts
    service, requests = local_provider
    additions, warnings = _extract_case_facts(service, {}, "intermittent warning")
    assert warnings == []
    assert all(value == [] for value in additions.values())
    assert requests[0]["response_format"] == {"type": "json_object"}


def test_copilot_fact_extraction_coerces_string_and_null_fields(local_provider, monkeypatch):
    from api.routes import diagnostics
    monkeypatch.setattr(diagnostics, "_parse_json_object", lambda raw: {
        "symptoms": "hydraulic leak", "observations": None,
        "checks_done": ["visual check"], "ruled_out": [],
    })
    additions, warnings = diagnostics._extract_case_facts(local_provider[0], {}, "hydraulic leak")
    assert warnings == []
    assert additions["symptoms"] == ["hydraulic leak"]
    assert additions["observations"] == []
    assert additions["checks_done"] == ["visual check"]
    assert additions["ruled_out"] == []


@pytest.mark.parametrize('json_mode', [False, True])
def test_local_token_cutoff_rejects_prose_without_changing_json_extraction(monkeypatch, json_mode):
    original = httpx.Client
    def client(**kwargs):
        return original(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            'choices': [{'message': {'content': 'unfinished'}, 'finish_reason': 'length'}]})), **kwargs)
    monkeypatch.setattr(httpx, 'Client', client)
    service = GroqService('synthetic', provider='openai_compatible', openai_compat_base_url='http://model.test/v1')
    if json_mode:
        assert service.chat([], json_mode=True) == 'unfinished'
    else:
        with pytest.raises(RuntimeError, match='incomplete content'):
            service.chat([])


@pytest.mark.parametrize('json_mode', [False, True])
def test_groq_token_cutoff_rejects_prose_without_changing_json_extraction(json_mode):
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='unfinished'), finish_reason='length')], usage=None)
    service = GroqService('', demo_mode=True)
    service.demo_mode = False
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
    if json_mode:
        assert service.chat([], json_mode=True) == 'unfinished'
    else:
        with pytest.raises(RuntimeError, match='incomplete content'):
            service.chat([])
