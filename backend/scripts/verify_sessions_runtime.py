"""Local-only production-startup smoke for persisted investigations.

Requires SESSION_SMOKE_ADMIN_EMAIL/PASSWORD and SESSION_SMOKE_FIXTURE_PATH.
Never run against shared staging: this script intentionally creates test users,
records and sessions in disposable local databases.
"""
from __future__ import annotations

import json
import os
import uuid
from urllib.parse import urlparse

import httpx


def main():
    base = os.getenv('SESSION_SMOKE_BASE_URL', 'http://127.0.0.1:18000')
    if urlparse(base).hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise RuntimeError('Session smoke requires an isolated loopback server, never staging.')
    email = os.environ['SESSION_SMOKE_ADMIN_EMAIL']
    password = os.environ['SESSION_SMOKE_ADMIN_PASSWORD']
    fixture = os.environ['SESSION_SMOKE_FIXTURE_PATH']
    suffix = uuid.uuid4().hex[:10]
    proof = {}
    with httpx.Client(base_url=base, timeout=30) as admin:
        health = admin.get('/api/health').json()
        assert health['graph_mode'] == 'neo4j' and health['auth_db_mode'] == 'postgresql', health
        assert health['llm_mode'] == 'fallback', health
        login = admin.post('/api/auth/login', json={'email': email, 'password': password})
        login.raise_for_status()
        admin.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
        proof['initial_health'] = health
        ingest = admin.post('/api/maintenance/ingest', json={'csv_path': fixture})
        ingest.raise_for_status()
        assets = admin.get('/api/maintenance/assets').json()
        # Existing maintenance response is a list, unchanged by the sessions API.
        asset = next(a for a in assets if a['tail_number'] == 'N-CI-123')
        credentials = {}
        for name in ['owner', 'other']:
            invite = admin.post('/api/admin/invites', json={
                'email': f'{name}-{suffix}@sessions.test', 'full_name': name, 'role': 'technician',
            })
            invite.raise_for_status()
            accepted = admin.post('/api/auth/invites/accept', json={
                'token': invite.json()['invite_token'], 'password': 'SessionSmokePassword2026', 'full_name': name,
            })
            accepted.raise_for_status()
            credentials[name] = {'Authorization': 'Bearer ' + accepted.json()['access_token']}
        with httpx.Client(base_url=base, headers=credentials['owner'], timeout=30) as browser:
            created = browser.post('/api/sessions', json={'title': 'Runtime smoke', 'asset_id': asset['id']})
            assert created.status_code == 201, created.text
            session_id = created.json()['id']
            path = f'/api/sessions/{session_id}'
            turn = browser.post(path + '/turns', json={'message': 'hydraulic pressure dropped during taxi'})
            assert turn.status_code == 200, turn.text
            body = turn.json()
            assert body['ranked_checks'] and body['evidence'] and body['reply'], body
            assert body['llm_status'] == 'unavailable', body
            beliefs = body['beliefs']
            assert beliefs['calibrated'] is False and beliefs['label'] == 'relative support'
            assert abs(sum(h['belief'] for h in beliefs['hypotheses']) + beliefs['other'] - 1) < 1e-9
            assert body['decision'] == 'abstain' and body['policy_status'] == 'not_configured'
            assert body['policy_inputs']['parameters'] is None
            proof['turn'] = {'turn_index': body['turn_index'], 'llm_status': body['llm_status'],
                             'evidence_count': len(body['evidence']), 'ranked_checks_count': len(body['ranked_checks']),
                             'template_present': 'not written by a model' in body['reply'],
                             'beliefs_normalized': True, 'calibrated': beliefs['calibrated'],
                             'belief_entropy': beliefs['entropy'], 'policy_status': body['policy_status']}
        with httpx.Client(base_url=base, headers=credentials['owner'], timeout=30) as second_browser:
            saved = second_browser.get(path)
            assert saved.status_code == 200
            assert saved.json()['turns'][0]['response'] == body
            snapshot = saved.json()['turns'][0]['snapshot']
            assert snapshot['hypotheses'] == beliefs['hypotheses']
            assert snapshot['belief_entropy'] == beliefs['entropy']
            proof['cross_client_replay_equal'] = True
            assert admin.get(path).status_code == 200
            assert admin.post(path + '/turns', json={'message': 'forbidden'}).status_code == 403
            foreign = admin.get(path, headers=credentials['other'])
            assert foreign.status_code == 404
            proof['other_technician_status'] = foreign.status_code
            closed = second_browser.post(path + '/close', json={
                'outcome_note': 'Synthetic runtime smoke outcome, not a real repair.', 'outcome_part': 'Hydraulic Pump',
            })
            assert closed.status_code == 200, closed.text
            assert second_browser.post(path + '/turns', json={'message': 'closed'}).status_code == 409
            report = second_browser.get(path + '/report')
            assert report.status_code == 200 and 'CI-SMOKE-001' in report.text
            proof['closed_report_status'] = report.status_code
            proof['closed_session_id'] = session_id
        proof['post_ingest_health'] = admin.get('/api/health').json()
    print(json.dumps(proof, indent=2))
    print('SESSION_RUNTIME_SMOKE=PASS')


if __name__ == '__main__':
    main()
