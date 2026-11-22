"""Replay retained real-reference evidence without networking or new model calls."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from investigation.experiments.model_compare import assess, load_packet
from investigation.experiments.model_prompts import fingerprint, messages


def read(path):
    return json.loads(path.read_text())


def verify(directory):
    directory = Path(directory)
    status = read(directory / 'status.json')
    provenance = read(directory / 'server-provenance.json')
    before, after = [read(directory / ('health-' + name + '.json'))
                     for name in ('before', 'after')]
    assert status['complete'] is True and status['m4_measurement'] is False
    assert provenance['m4_measurement'] is False
    assert provenance['public_model_ports'] is False
    assert provenance['database_writes'] is False
    assert provenance['model_pulls_or_configuration_changes'] is False
    assert status['source_sha'] == provenance['source_sha'] == before['git_sha'] == after['git_sha']
    assert before['maintenance_record_count'] == after['maintenance_record_count']
    assert before['maintenance_record_count'] > 0
    for value in (before, after):
        assert value['graph_mode'] == 'neo4j' and value['llm_mode'] == 'live'
        assert value['auth_db_mode'] == 'postgresql' and value['auth_enabled'] is True
        assert value['openapi_enabled'] is False
    comparison = directory / 'comparison'
    packet = load_packet(comparison / 'packet.json')
    original = load_packet(ROOT / 'backend/investigation/experiments/data/model_prompts_2024_v1.json')
    assert packet == original
    plan = read(comparison / 'manifest.json')['plan']
    result = read(comparison / 'results.json')
    assert plan['execution_source'] == 'ollama_http'
    assert plan['measurement_role'] == result['measurement_role'] == 'staging_reference'
    assert plan['hardware']['system'] == 'Linux'
    assert plan['server_hardware_verified'] is False
    assert plan['checker'] is None and result['checker'] is None
    assert plan['packet_sha256'] == result['packet_sha256'] == packet['packet_sha256']
    assert plan['generation'] == {'temperature': 0, 'num_predict': 700,
                                  'num_ctx': 4096, 'keep_alive': '5m'}
    methods = {name: ROOT / 'backend' / path for name, path in {
        'model_compare.py': 'investigation/experiments/model_compare.py',
        'model_prompts.py': 'investigation/experiments/model_prompts.py',
        'grounding.py': 'investigation/grounding.py',
        'grounding_parts_v1.json': 'investigation/data/grounding_parts_v1.json'}.items()}
    assert plan['method_files_sha256'] == {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                          for name, path in methods.items()}
    assert len(plan['models']) == 1 and plan['models'][0].split(':')[0] == 'phi4-mini'
    model = plan['models'][0]
    assert plan['model_identities'][model]['digest']
    assert result['complete'] is True and result['selected_model'] is None
    assert result['held_out_2025_used'] is False
    journal = comparison / 'responses.jsonl'
    raw = journal.read_bytes()
    assert raw.endswith(b'\n')
    assert hashlib.sha256(raw).hexdigest() == result['journal_sha256']
    rows = [json.loads(line) for line in raw.splitlines()]
    cases = {case['case_id']: case for case in packet['cases']}
    expected = {(model, case['case_id'], arm) for case in cases.values()
                for arm in (('evidence', 'no_evidence') if case['task'] == 'prose' else ('evidence',))}
    assert len(rows) == len(expected) == result['n_attempts'] == 30
    assert {(r['model'], r['case_id'], r['arm']) for r in rows} == expected
    assert result['provider_errors'] == 0 and result['n_responses'] == 30
    for row in rows:
        assert not row.get('error') and row['raw']['model'] == model
        assert math.isfinite(row['wall_seconds']) and row['wall_seconds'] >= 0
        case = cases[row['case_id']]
        assert row['task'] == case['task']
        assert row['prompt_sha256'] == fingerprint(messages(case, baseline=row['arm'] == 'no_evidence'))
        assert row['assessment'] == assess(row['raw'], case, baseline=row['arm'] == 'no_evidence')
    warmups = [json.loads(line) for line in (comparison / 'warmups.jsonl').read_text().splitlines()]
    assert len(warmups) == 1 and warmups[0]['model'] == model
    assert warmups[0]['raw']['done'] is True
    assert warmups[0]['raw']['model'] == model
    groups = Counter((r['arm'], r['task']) for r in rows)
    assert groups == {('evidence', 'facts'): 10, ('evidence', 'prose'): 10,
                      ('no_evidence', 'prose'): 10}
    assert len(result['summaries']) == 3
    assert {(s['arm'], s['task']) for s in result['summaries']} == set(groups)
    summary = []
    for saved in result['summaries']:
        group = [r for r in rows if (r['arm'], r['task']) == (saved['arm'], saved['task'])]
        assert saved['model'] == model and saved['n_attempted'] == saved['n_responses'] == 10
        checks = [row['assessment'] for row in group]
        valid = sum(row['valid_output'] for row in checks)
        citations = sum(row.get('citation_occurrences', 0) for row in checks)
        good = sum(row.get('in_evidence_citation_occurrences', 0) for row in checks)
        sentences = sum(row.get('sentence_count', 0) for row in checks)
        unrated = sum(row.get('unrated_sentences', 0) for row in checks)
        unsupported = sum(row.get('unsupported_or_unapproved_uncited_sentences', 0) for row in checks)
        assert saved['valid_output_share'] == valid / 10
        assert saved['citation_occurrences'] == citations
        assert saved['in_evidence_citation_share'] == (good / citations if citations else None)
        assert saved['sentence_count'] == sentences and saved['unrated_sentences'] == unrated
        assert saved['unsupported_or_unapproved_uncited_sentences'] == unsupported
        assert saved['unsupported_rate'] is None  # No accepted/experimental thresholds installed.
        assert saved['seconds_per_attempt_mean'] == statistics.mean(r['wall_seconds'] for r in group)
        assert saved['seconds_per_response_median'] == statistics.median(r['wall_seconds'] for r in group)
        summary.append({'arm': saved['arm'], 'task': saved['task'], 'attempts': 10,
                        'valid_outputs': valid, 'citation_occurrences': citations,
                        'in_evidence_citations': good, 'sentences': sentences,
                        'unrated': unrated, 'unsupported_or_uncited': unsupported,
                        'mean_wall_seconds': saved['seconds_per_attempt_mean']})
    return {'verified': True, 'source_sha': status['source_sha'], 'model': model,
            'packet_sha256': packet['packet_sha256'], 'n_attempts': 30,
            'excluded_warmups': 1, 'summaries': summary,
            'human_accuracy_measured': False, 'm4_measurement': False,
            'note': 'No new model calls; raw audit replay and independent scalar summary arithmetic.'}


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1]), indent=2, allow_nan=False))
