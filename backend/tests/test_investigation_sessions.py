"""Session lifecycle/access tests through real JWTs and durable SQL storage."""
from concurrent.futures import ThreadPoolExecutor
import threading
import os
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from db.models import Organization, User
from db.session import normalize_database_url
from db.models.sessions import DiagnosticSession, SessionSnapshot, SessionTurn
from services.auth_service import hash_password
from tests.conftest import _build_test_app
from tests.test_auth_rbac import ADMIN_EMAIL, ADMIN_PASS, _auth_settings, _invite_and_accept, _login
from tests.test_api_copilot import seed_case


@pytest.fixture(params=['sqlite', 'postgresql'])
def environment(tmp_path, request):
    admin_engine = None
    schema = None
    overrides = {'RATE_LIMIT_ENABLED': False}
    if request.param == 'postgresql':
        url = os.getenv('SESSION_TEST_DATABASE_URL')
        if not url:
            pytest.skip('SESSION_TEST_DATABASE_URL not set — PostgreSQL session tests skipped')
        # Own random schema, never wipe an existing database or someone else's records.
        url = normalize_database_url(url)
        admin_engine = create_engine(url)
        schema = 'session_test_' + uuid.uuid4().hex
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA {schema}'))
        overrides['DATABASE_URL'] = make_url(url).update_query_dict(
            {'options': '-csearch_path=' + schema}).render_as_string(hide_password=False)
    settings = _auth_settings(tmp_path, **overrides)
    app = _build_test_app(settings)
    with TestClient(app) as client:
        admin = _login(client, ADMIN_EMAIL, ADMIN_PASS)
        users = {'admin': admin}
        for key, role in [('owner', 'technician'), ('other', 'technician'), ('supervisor', 'supervisor')]:
            users[key] = _invite_and_accept(client, admin['access_token'], email=f'{key}@sessions.test',
                                            full_name=key, role=role)
        headers = {k: {'Authorization': f"Bearer {v['access_token']}"} for k, v in users.items()}
        asset_id = seed_case(app)
        yield client, app, settings, users, headers, asset_id
    app.state.rel_store.close()
    if admin_engine is not None:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin_engine.dispose()


def create(client, headers, asset_id=None, title='Pump investigation'):
    response = client.post('/api/sessions', json={'asset_id': asset_id, 'title': title}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_session_replays_across_clients_and_application_restart(environment):
    client, app, settings, _, headers, asset = environment
    row = create(client, headers['owner'], asset)
    path = f"/api/sessions/{row['id']}"
    result = client.post(path + '/turns', json={'message': 'hydraulic pump leak'}, headers=headers['owner'])
    assert result.status_code == 200, result.text
    response = result.json()
    assert response['session_id'] == row['id']
    assert response['llm_status'] == 'unavailable'
    assert response['ranked_checks'] and response['evidence']
    assert response['citation_validation']['valid_ids']
    assert response['reply'] and 'not written by a model' in response['reply']
    assert response['policy_status'] == 'not_configured'
    assert response['beliefs']['calibrated'] is False
    assert response['decision'] == 'abstain'
    assert response['policy_inputs']['parameters'] is None
    with TestClient(app) as second_browser:
        saved = second_browser.get(path, headers=headers['owner']).json()
    assert saved['turns'][0]['response'] == response
    assert saved['turns'][0]['snapshot']['evidence_ids'] == [r['record_id'] for r in response['evidence']]
    assert saved['turn_count'] == 1
    assert saved['turns'][0]['snapshot']['belief_entropy'] == response['beliefs']['entropy']
    assert saved['turns'][0]['snapshot']['hypotheses'] == response['beliefs']['hypotheses']
    app.state.graph_repo.update_service_record('AALA2024050500004', {'text': 'changed after the turn'})
    assert client.get(path, headers=headers['owner']).json()['turns'][0]['response'] == response
    # New app/engine, same file database. No browser storage or shared in-process object required.
    restarted = _build_test_app(settings)
    with TestClient(restarted) as fresh:
        assert fresh.get(path, headers=headers['owner']).json()['turns'][0]['response'] == response
    restarted.state.rel_store.close()


def test_close_outcome_and_read_only_replay(environment):
    client, _, _, _, h, asset = environment
    row = create(client, h['owner'], asset)
    path = f"/api/sessions/{row['id']}"
    assert client.post(path + '/close', json={'outcome_note': ' '}, headers=h['owner']).status_code == 422
    closed = client.post(path + '/close', json={
        'outcome_part': 'PUMP', 'outcome_jasc': '2900', 'outcome_note': 'Pump leak found.',
        'outcome_record_id': 'AALA2024050500004',
    }, headers=h['owner'])
    assert closed.status_code == 200, closed.text
    assert closed.json()['closed_at'] and closed.json()['status'] == 'closed'
    assert client.post(path + '/turns', json={'message': 'retry'}, headers=h['owner']).status_code == 409
    assert client.post(path + '/close', json={'outcome_note': 'overwrite'}, headers=h['owner']).status_code == 409
    assert client.get(path, headers=h['owner']).json()['can_write'] is False
    listed = client.get('/api/sessions?status=closed&has_outcome=true', headers=h['supervisor']).json()
    assert listed['items'][0]['outcome_part'] == 'PUMP'
    summary = client.get('/api/sessions/summary', headers=h['owner']).json()
    assert summary['stats'] == [{'label': 'Open investigations', 'value': 0},
                                 {'label': 'Closed investigations', 'value': 1}]


def test_other_technician_cannot_discover_read_or_write(environment):
    client, _, _, _, h, asset = environment
    row = create(client, h['owner'], asset)
    path = f"/api/sessions/{row['id']}"
    assert client.get('/api/sessions', headers=h['other']).json()['items'] == []
    assert client.get(path, headers=h['other']).status_code == 404
    assert client.post(path + '/turns', json={'message': 'hello'}, headers=h['other']).status_code == 404
    assert client.post(path + '/close', json={'outcome_note': 'hello'}, headers=h['other']).status_code == 404
    assert client.get(path + '/report', headers=h['other']).status_code == 404


@pytest.mark.parametrize('role', ['supervisor', 'admin'])
def test_organization_supervisors_can_read_but_not_write_others(environment, role):
    client, _, _, _, h, asset = environment
    row = create(client, h['owner'], asset)
    path = f"/api/sessions/{row['id']}"
    assert client.get(path, headers=h[role]).status_code == 200
    assert client.get(path, headers=h[role]).json()['can_write'] is False
    assert len(client.get('/api/sessions', headers=h[role]).json()['items']) == 1
    assert client.get('/api/sessions?mine=true', headers=h[role]).json()['items'] == []
    assert client.post(path + '/turns', json={'message': 'hello'}, headers=h[role]).status_code == 403
    assert client.post(path + '/close', json={'outcome_note': 'hello'}, headers=h[role]).status_code == 403


def test_other_organization_is_hidden_even_from_admin(environment):
    client, app, _, _, h, asset = environment
    row = create(client, h['owner'], asset)
    with app.state.rel_store.session_scope() as db:
        org = Organization(slug='second-org', name='Second org')
        db.add(org)
        db.flush()
        db.add(User(organization_id=org.id, email='foreign@sessions.test', full_name='Foreign admin',
                    password_hash=hash_password('OtherOrgPassword2026'), role='admin'))
    foreign = _login(client, 'foreign@sessions.test', 'OtherOrgPassword2026')
    header = {'Authorization': f"Bearer {foreign['access_token']}"}
    assert client.get('/api/sessions', headers=header).json()['items'] == []
    assert client.get(f"/api/sessions/{row['id']}", headers=header).status_code == 404
    assert client.post(f"/api/sessions/{row['id']}/close", json={'outcome_note': 'x'}, headers=header).status_code == 404


def test_service_tokens_cannot_access_user_sessions(environment):
    client, _, settings, _, h, _ = environment
    row = create(client, h['owner'])
    for header in [{'X-Halite-Api-Key': settings.HALITE_API_KEY}, {'X-Ops-Token': settings.OPS_TOKEN}]:
        assert client.post('/api/sessions', json={}, headers=header).status_code == 403
        assert client.get('/api/sessions', headers=header).status_code == 403
        assert client.get(f"/api/sessions/{row['id']}", headers=header).status_code == 403
        assert client.get('/api/sessions/summary', headers=header).json()['stats'] == []


def test_pagination_filters_and_request_validation(environment):
    client, _, _, _, h, _ = environment
    ids = {create(client, h['owner'], title=f'Case {i}')['id'] for i in range(3)}
    first = client.get('/api/sessions?limit=2', headers=h['owner']).json()
    second = client.get('/api/sessions', params={'limit': 2, 'cursor': first['next_cursor']}, headers=h['owner']).json()
    assert {r['id'] for r in first['items'] + second['items']} == ids
    assert len(first['items']) == 2 and len(second['items']) == 1 and second['next_cursor'] is None
    assert client.get('/api/sessions?status=closed', headers=h['owner']).json()['items'] == []
    for query in ['limit=0', 'limit=101', 'status=invalid', 'cursor=broken']:
        assert client.get('/api/sessions?' + query, headers=h['owner']).status_code == 422
    row_id = first['items'][0]['id']
    assert client.post('/api/sessions', json={'asset_id': 'unknown'}, headers=h['owner']).status_code == 404
    assert client.post(f'/api/sessions/{row_id}/turns', json={'message': ' '}, headers=h['owner']).status_code == 422
    assert client.post(f'/api/sessions/{row_id}/turns', json={
        'message': 'answer', 'answer': {'attribute': 'stage', 'value': 'A'},
    }, headers=h['owner']).status_code == 409


def test_concurrent_turns_cannot_overwrite_each_other(environment, monkeypatch):
    client, app, _, _, h, _ = environment
    row = create(client, h['owner'])
    import investigation.sessions as module
    original = module.run_turn
    barrier = threading.Barrier(2)

    def simultaneous(**kwargs):
        result = original(**kwargs)
        barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(module, 'run_turn', simultaneous)
    def send(message):
        with TestClient(app) as browser:
            return browser.post(f"/api/sessions/{row['id']}/turns", json={'message': message}, headers=h['owner'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, ['pump leak', 'smoke']))
    assert sorted(r.status_code for r in responses) == [200, 409]
    saved = client.get(f"/api/sessions/{row['id']}", headers=h['owner']).json()
    assert saved['turn_count'] == 1 and len(saved['turns']) == 1
    with app.state.rel_store.session_scope() as db:
        assert db.scalar(select(func.count()).select_from(SessionSnapshot)) == 1


def test_close_during_inference_discards_stale_turn(environment, monkeypatch):
    client, app, _, _, h, _ = environment
    row = create(client, h['owner'])
    import investigation.sessions as module
    original = module.run_turn
    def close_first(**kwargs):
        result = original(**kwargs)
        closed = client.post(f"/api/sessions/{row['id']}/close", json={'outcome_note': 'Closed during inference'}, headers=h['owner'])
        assert closed.status_code == 200
        return result
    monkeypatch.setattr(module, 'run_turn', close_first)
    result = client.post(f"/api/sessions/{row['id']}/turns", json={'message': 'pump'}, headers=h['owner'])
    assert result.status_code == 409
    with app.state.rel_store.session_scope() as db:
        assert db.get(DiagnosticSession, row['id']).turn_count == 0
        assert db.scalar(select(func.count()).select_from(SessionTurn)) == 0
        assert db.scalar(select(func.count()).select_from(SessionSnapshot)) == 0


def test_printable_report_escapes_text_and_preserves_citations(environment):
    client, _, _, _, h, asset = environment
    row = create(client, h['owner'], asset, '<script>alert(1)</script>')
    path = f"/api/sessions/{row['id']}"
    assert client.get(path + '/report', headers=h['owner']).status_code == 409
    assert client.post(path + '/turns', json={'message': 'pump leak'}, headers=h['owner']).status_code == 200
    assert client.post(path + '/close', json={'outcome_note': '<img src=x onerror=alert(1)>'}, headers=h['owner']).status_code == 200
    report = client.get(path + '/report', headers=h['owner'])
    assert report.status_code == 200
    assert '<script>' not in report.text and '<img' not in report.text
    assert '&lt;script&gt;' in report.text and 'AALA2024050500004' in report.text
    assert report.headers['cache-control'] == 'no-store'


def test_server_state_cannot_be_replaced_by_browser_payload(environment):
    client, _, _, _, h, _ = environment
    row = create(client, h['owner'])
    path = f"/api/sessions/{row['id']}/turns"
    first = client.post(path, json={'message': 'pump leak'}, headers=h['owner'])
    assert first.status_code == 200
    second = client.post(path, json={
        'message': 'smoke observed', 'case_state': {'symptoms': ['injected'], 'ruled_out': ['PUMP']},
    }, headers=h['owner'])
    assert second.status_code == 200
    assert second.json()['case_state']['symptoms'] == ['pump leak', 'smoke observed']
    assert second.json()['case_state']['ruled_out'] == []
    assert second.json()['turn_index'] == 2


def test_snapshot_failure_rolls_back_turn_and_revision(environment, monkeypatch):
    client, app, _, _, h, _ = environment
    row = create(client, h['owner'])
    import investigation.sessions as module
    original = module.SessionSnapshot
    def fail_snapshot(**kwargs):
        raise RuntimeError('test snapshot persistence failure')
    monkeypatch.setattr(module, 'SessionSnapshot', fail_snapshot)
    with TestClient(app, raise_server_exceptions=False) as browser:
        failed = browser.post(f"/api/sessions/{row['id']}/turns", json={'message': 'pump leak'}, headers=h['owner'])
    assert failed.status_code == 500
    with app.state.rel_store.session_scope() as db:
        assert db.get(DiagnosticSession, row['id']).turn_count == 0
        assert db.scalar(select(func.count()).select_from(SessionTurn)) == 0
        assert db.scalar(select(func.count()).select_from(SessionSnapshot)) == 0
    monkeypatch.setattr(module, 'SessionSnapshot', original)
    retried = client.post(f"/api/sessions/{row['id']}/turns", json={'message': 'pump leak'}, headers=h['owner'])
    assert retried.status_code == 200 and retried.json()['turn_index'] == 1
