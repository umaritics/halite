"""Unplug and cache correctness tests for quick diagnosis and citation allow-lists."""
import json

from api.routes import diagnostics
from services.citation_validation import validate_citations
from tests.test_api_diagnostics import _DeadGroq, _LiveGroq, _seed_faa_asset


class FailingModel(_LiveGroq):
    def chat(self, *args, **kwargs):
        raise RuntimeError('model disconnected')


def test_degraded_is_opt_in_and_retains_ranking_and_evidence(client):
    asset = _seed_faa_asset(client.app)
    client.app.state.groq_service = _DeadGroq()
    payload = {'asset_id': asset, 'symptom_text': 'hydraulic leak'}
    assert client.post('/api/maintenance/diagnose', json=payload).status_code == 503
    result = client.post('/api/maintenance/diagnose', json={**payload, 'allow_degraded': True})
    assert result.status_code == 200
    body = result.json()
    assert body['explanation'] is None
    assert body['llm_status'] == 'unavailable'
    assert body['ranked_checks'] and body['evidence']
    assert 'not written by a model' in body['fallback_explanation']
    assert body['warnings']


def test_degraded_handles_provider_failure_and_empty_explanation(client):
    asset = _seed_faa_asset(client.app)
    payload = {'asset_id': asset, 'symptom_text': 'pump leak', 'allow_degraded': True}
    for model in [FailingModel('unused'), _LiveGroq('')]:
        client.app.state.groq_service = model
        result = client.post('/api/maintenance/diagnose', json=payload)
        assert result.status_code == 200, result.text
        assert result.json()['explanation'] is None
        assert result.json()['fallback_explanation']


def test_degraded_unknown_aircraft_fails_cleanly(client):
    result = client.post('/api/maintenance/diagnose', json={
        'asset_id': 'unknown', 'symptom_text': 'leak', 'allow_degraded': True,
    })
    assert result.status_code == 404


def test_existing_but_unshown_citation_is_not_verified(client):
    asset = _seed_faa_asset(client.app)
    repo = client.app.state.graph_repo
    repo.create_service_record({'record_id': 'ZZZZ2024123456789', 'text': 'unrelated galley cleaning',
                                'part_name': 'OVEN', 'occurred_at': '2024-01-01'})
    client.app.state.groq_service = _LiveGroq('Pump leak in SWIA2025091876593. Also ZZZZ2024123456789.')
    result = client.post('/api/maintenance/diagnose', json={'asset_id': asset, 'symptom_text': 'pump leak'})
    assert result.status_code == 200
    body = result.json()
    assert 'ZZZZ2024123456789' in body['citation_validation']['invalid_ids']
    assert 'ZZZZ2024123456789' not in body['citation_validation']['valid_ids']
    assert '[UNVERIFIED:ZZZZ2024123456789]' in body['explanation']
    direct = validate_citations('SWIA2025091876593', repo, allowed_ids=set())
    assert direct['valid'] == [] and direct['invalid'] == ['SWIA2025091876593']


def test_cache_invalidates_when_evidence_changes_without_record_count_change(client, monkeypatch, tmp_path):
    asset = _seed_faa_asset(client.app)
    calls = []
    class CountingModel(_LiveGroq):
        def chat(self, *args, **kwargs):
            calls.append(1)
            return super().chat(*args, **kwargs)
    client.app.state.groq_service = CountingModel('Pump leak in SWIA2025091876593.')
    monkeypatch.setattr(diagnostics, '_cache_path', lambda: tmp_path / 'cache.json')
    # Exercise production cache semantics, not the existing test-only cache bypass.
    monkeypatch.delenv('PYTEST_CURRENT_TEST')
    payload = {'asset_id': asset, 'symptom_text': 'pump leak'}
    assert client.post('/api/maintenance/diagnose', json=payload).status_code == 200
    assert client.post('/api/maintenance/diagnose', json=payload).status_code == 200
    assert len(calls) == 1
    repo = client.app.state.graph_repo
    count = repo.count_service_records()
    repo.update_service_record('SWIA2025091876593', {'status': 'superseded', 'text': 'original report corrected'})
    assert repo.count_service_records() == count
    assert client.post('/api/maintenance/diagnose', json=payload).status_code == 200
    assert len(calls) == 2
    monkeypatch.setattr(client.app.state.settings, 'RETRIEVAL_MODE', 'mid_fixed')
    assert client.post('/api/maintenance/diagnose', json=payload).status_code == 200
    assert len(calls) == 3
    assert all(r.get('explanation') for r in json.loads((tmp_path / 'cache.json').read_text()).values())


def test_empty_cached_explanation_is_never_served(client, monkeypatch):
    asset = _seed_faa_asset(client.app)
    client.app.state.groq_service = _DeadGroq()
    class EmptyCache(dict):
        def get(self, key, default=None):
            return {'explanation': ''}
    monkeypatch.setattr(diagnostics, '_load_cache', EmptyCache)
    monkeypatch.delenv('PYTEST_CURRENT_TEST')
    response = client.post('/api/maintenance/diagnose', json={
        'asset_id': asset, 'symptom_text': 'leak', 'allow_degraded': True,
    })
    assert response.status_code == 200
    assert response.json()['fallback_explanation']
    assert response.json()['explanation'] is None


def test_malformed_cache_shape_is_ignored(monkeypatch, tmp_path):
    path = tmp_path / 'cache.json'
    monkeypatch.setattr(diagnostics, '_cache_path', lambda: path)
    for value in ['[]', 'null', '{not json']:
        path.write_text(value)
        assert diagnostics._load_cache() == {}


def test_non_text_explanation_and_null_rare_cases_do_not_crash(client):
    asset = _seed_faa_asset(client.app)
    class WrongShape(_LiveGroq):
        def chat(self, *args, **kwargs):
            return json.dumps({'explanation': ['bad shape'], 'rare_cases': None})
    client.app.state.groq_service = WrongShape('unused')
    response = client.post('/api/maintenance/diagnose', json={
        'asset_id': asset, 'symptom_text': 'leak', 'allow_degraded': True,
    })
    assert response.status_code == 200
    assert response.json()['explanation'] is None
