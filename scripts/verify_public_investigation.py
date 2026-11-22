"""Explicit dedicated-account lifecycle check; no corpus/user administration writes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

API = 'https://dev1.corp.curatech.pk/halite-api/api'
TITLE = 'Automated acceptance check - no maintenance finding'
MESSAGE = ('Synthetic acceptance scenario only, not an observed fault: '
           'hydraulic pressure drops during taxi. Explain the historical evidence.')
OUTCOME = 'Synthetic acceptance scenario only. No actual maintenance finding, repair, or airworthiness decision.'


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(method, path, *, token='', data=None, expected=200, timeout=30):
    assert path.startswith('/') and not path.startswith('//')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(API + path, method=method, headers=headers,
                                 data=json.dumps(data).encode() if data is not None else None)
    try:
        response = urllib.request.build_opener(NoRedirects).open(req, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        code, content = response.code, response.read().decode('utf-8')
        content_type = response.headers.get('Content-Type', '')
    assert code == expected, f'Unexpected HTTP status {code}'
    return json.loads(content) if 'application/json' in content_type else content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirmation', required=True, choices=['VERIFY_SESSION'])
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}', args.expected_sha)
    assert os.environ.get('HALITE_UI_TEST_EMAIL') and os.environ.get('HALITE_UI_TEST_PASSWORD')
    args.output.mkdir(parents=True, exist_ok=False)
    proof = {'schema': 'halite-public-session-v1', 'state': 'running',
             'started_at': datetime.now(timezone.utc).isoformat(), 'stage': 'health-before',
             'corpus_writes': False, 'admin_or_other_account_writes': False,
             'synthetic_case': True, 'outcome_part_recorded': False, 'checks': {}}
    secrets = [os.environ['HALITE_UI_TEST_PASSWORD']]
    token = refresh = ''
    def write(name, value):
        text = json.dumps(value, indent=2, allow_nan=False) + '\n'
        assert all(secret not in text for secret in secrets if secret), 'Sensitive output rejected'
        (args.output / name).write_text(text)
    def stage(value):
        proof['stage'] = value
        write('verification.json', proof)
        print(json.dumps({'stage': value, 'session_id': proof.get('session_id')}), flush=True)
    try:
        before = request('GET', '/health')
        assert before['git_sha'] == args.expected_sha
        assert before['graph_mode'] == 'neo4j' and before['llm_mode'] == 'live'
        assert before['auth_db_mode'] == 'postgresql' and before['maintenance_corpus_loaded']
        write('health-before.json', before)
        stage('login')
        login = request('POST', '/auth/login', data={'email': os.environ['HALITE_UI_TEST_EMAIL'],
                                                    'password': os.environ['HALITE_UI_TEST_PASSWORD']})
        token, refresh = login['access_token'], login['refresh_token']
        secrets.extend([token, refresh])
        actor = login['user']['id']
        stage('select-existing-aircraft')
        assets = request('GET', '/maintenance/assets', token=token)
        asset = max(assets, key=lambda item: item['record_count'])
        assert asset['record_count'] > 0
        proof['asset_id'], proof['asset_tail'] = asset['id'], asset['tail_number']
        stage('create-labelled-case')
        case = request('POST', '/sessions', token=token, data={'title': TITLE, 'asset_id': asset['id']}, expected=201)
        proof['session_id'] = case['id']
        write('created-session.json', case)
        assert case['user_id'] == actor and case['status'] == 'open'
        path = '/sessions/' + case['id']
        assert request('GET', path, token=token)['turns'] == []
        stage('single-model-backed-turn-no-retry')
        started = time.monotonic()
        result = request('POST', path + '/turns', token=token, data={'message': MESSAGE}, timeout=300)
        proof['turn_wall_seconds'] = time.monotonic() - started
        write('turn-response.json', result)
        assert result['reply'] and result['ranked_checks'] and result['evidence']
        assert result['beliefs']['label'] == 'relative support'
        proof['llm_status'] = result['llm_status']
        proof['live_prose_verified'] = result['llm_status'] == 'available'
        stage('independent-http-replay')
        saved = request('GET', path, token=token)
        assert len(saved['turns']) == 1 and saved['turns'][0]['response'] == result
        snapshot = saved['turns'][0]['snapshot']
        assert snapshot['hypotheses'] == result['beliefs']['hypotheses']
        assert snapshot['belief_entropy'] == result['beliefs']['entropy']
        write('saved-open.json', saved)
        proof['checks']['exact_response_and_snapshot_replay'] = True
        stage('close-without-a-maintenance-finding')
        request('POST', path + '/close', token=token, data={'outcome_note': OUTCOME})
        closed = request('GET', path, token=token)
        assert closed['status'] == 'closed' and closed['outcome_note'] == OUTCOME
        assert closed['outcome_part'] is None and closed['turns'][0]['response'] == result
        write('saved-closed.json', closed)
        proof['checks']['closed_exact_replay_no_training_part_label'] = True
        request('POST', path + '/turns', token=token, data={'message': 'Closed-case guard check'}, expected=409)
        proof['checks']['closed_write_rejected_409'] = True
        stage('authenticated-printable-report')
        report = request('GET', path + '/report', token=token)
        assert TITLE in report and OUTCOME in report and '<html' in report.lower()
        assert all(secret not in report for secret in secrets)
        (args.output / 'report.html').write_text(report)
        proof['checks']['printable_report'] = True
        after = request('GET', '/health')
        assert after['git_sha'] == before['git_sha']
        assert after['maintenance_record_count'] == before['maintenance_record_count']
        write('health-after.json', after)
        proof['checks']['deployed_source_and_corpus_unchanged'] = True
        proof['lifecycle_verified'] = True
        stage('live-prose-acceptance')
        assert proof['live_prose_verified'], 'Live prose unavailable; preserve explicit fallback evidence'
        proof['state'], proof['stage'] = 'passed', 'complete'
    except Exception as error:
        proof['state'] = 'failed'
        proof['failure'] = {'stage': proof['stage'], 'type': type(error).__name__}
    finally:
        if refresh:
            try:
                request('POST', '/auth/logout', token=token, data={'refresh_token': refresh})
                proof['logout'] = 'confirmed'
            except Exception as error:
                proof['logout'] = 'unconfirmed'
                proof['logout_error_type'] = type(error).__name__
                proof['state'] = 'failed'
        proof['finished_at'] = datetime.now(timezone.utc).isoformat()
        proof['client_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        write('verification.json', proof)
        print(json.dumps(proof), flush=True)
    return 0 if proof['state'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
