"""Provider formatting failures and prompt source boundaries stay explicit."""
import json
import pytest

from tests.test_api_diagnostics import _LiveGroq, _seed_faa_asset
from investigation.grounding_runtime import annotate_response
from tests.test_api_copilot import FakeCopilotLlm, seed_case


@pytest.mark.parametrize('raw', ['{"explanation":"cut off', '```json\n{"explanation":"cut off', '[{"explanation":"wrong shape"}]'])
def test_malformed_or_nonobject_quick_json_degrades_without_showing_fragments(client, raw):
    asset = _seed_faa_asset(client.app)
    class Broken(_LiveGroq):
        def chat(self, *args, **kwargs):
            return raw
    client.app.state.groq_service = Broken('unused')
    response = client.post('/api/maintenance/diagnose', json={
        'asset_id': asset, 'symptom_text': 'pump leak', 'allow_degraded': True})
    assert response.status_code == 200
    result = response.json()
    assert result['explanation'] is None and result['llm_status'] == 'unavailable'
    assert result['fallback_explanation'] and result['ranked_checks']
    assert raw not in result['fallback_explanation']


def test_complete_legacy_plain_text_quick_reply_remains_compatible(client):
    asset = _seed_faa_asset(client.app)
    text = '[SWIA2025091876593] Hydraulic pump leak at seal.'
    class Plain(_LiveGroq):
        def chat(self, *args, **kwargs):
            assert kwargs['json_mode'] is True and kwargs['max_tokens'] == 512
            return text
    client.app.state.groq_service = Plain('unused')
    result = client.post('/api/maintenance/diagnose', json={'asset_id': asset, 'symptom_text': 'pump leak'}).json()
    assert result['explanation'] == text


def test_sentence_membership_uses_actual_model_sources_but_fallback_keeps_saved_sources():
    evidence = [{'record_id': 'FAA2025000001', 'text': 'Pump leaked.'},
                {'record_id': 'FAA2025000002', 'text': 'Valve leaked.'}]
    response = {'reply': 'Valve leaked FAA2025000002.', 'evidence': evidence,
                'prose_context': {'accepted_as_reply': True, 'evidence_record_ids': ['FAA2025000001']}}
    annotate_response(response)
    assert [r['record_id'] for r in response['evidence']] == ['FAA2025000001', 'FAA2025000002']
    assert [r['record_id'] for r in response['grounding']['evidence']] == ['FAA2025000001']
    assert response['grounding']['sentences'][0]['invalid_citations'] == ['FAA2025000002']
    response['prose_context']['accepted_as_reply'] = False
    annotate_response(response)
    assert len(response['grounding']['evidence']) == 2


def test_existing_saved_record_outside_actual_model_prompt_is_flagged(client):
    asset = seed_case(client.app)
    known = ['SWIA2024010100001', 'SWIA2024020200002', 'SWIA2023030300003',
             'AALA2024050500004', 'AALA2022060600005']
    class Outside(FakeCopilotLlm):
        omitted = None
        def chat(self, messages, **kwargs):
            prompt = messages[-1]['content']
            if prompt.startswith('Extract NEW maintenance case facts'):
                return super().chat(messages, **kwargs)
            data = json.loads(prompt.split('\nDATA: ', 1)[1])
            supplied = {row[0] for row in data['evidence']}
            self.omitted = next(rid for rid in known if rid not in supplied)
            return f'Historical report {self.omitted} mentions a component.'
    model = Outside()
    client.app.state.groq_service = model
    response = client.post('/api/maintenance/copilot/turn', json={'asset_id': asset, 'message': 'hydraulic pressure loss'})
    assert response.status_code == 200
    result = response.json()
    assert model.omitted in {r['record_id'] for r in result['evidence']}
    assert model.omitted not in result['prose_context']['evidence_record_ids']
    assert result['citation_validation']['invalid_ids'] == [model.omitted]
    assert f'[UNVERIFIED:{model.omitted}]' in result['reply']
