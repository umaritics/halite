"""Independent scalar replay of every stopping-table metric; no graph/model/raw FAA."""
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3] / 'backend/investigation'


def independent(cases, baseline, point, protocol):
    totals = [0] * 6
    for case in cases:
        hypotheses = baseline[case['case_id']]['hypotheses'][:10]
        names = case['names']
        counts = {h['part_name']: h['evidence_count'] for h in hypotheses}
        trace = case['traces'][point['strategy']]
        for i, state in enumerate(trace):
            order = sorted(range(len(names)), key=lambda j: (-state['beliefs'][j], j))
            ranked = [names[j] for j in order]
            answered = bool(ranked) and state['beliefs'][order[0]] >= point['tau_answer'] and counts[ranked[0]] >= protocol['n_min']
            following = trace[i+1] if i+1 < len(trace) else None
            can_ask = (following is not None and following['attribute'] is not None
                       and following['questions_asked'] > state['questions_asked']
                       and state['questions_asked'] < protocol['max_questions']
                       and following['gain_bits'] >= point['g_min'])
            if answered or not can_ask:
                totals[0] += 1
                totals[1] += answered
                totals[2] += answered and bool(ranked) and ranked[0] == case['answer_part']
                totals[3] += answered and case['answer_part'] in ranked[:3]
                totals[4] += state['questions_asked']
                totals[5] += not answered
                break
        else:
            raise AssertionError('Independent replay exhausted the saved trajectory.')
    n, answered, top1, top3, questions, abstained = totals
    return {'n_pairs':n, 'n_originals':len({c['query_id'] for c in cases}), 'n_answered':answered,
            'n_correct_top1':top1, 'n_correct_top3':top3, 'coverage':answered/n,
            'accuracy_top1':top1/answered if answered else None,
            'accuracy_top3':top3/answered if answered else None,
            'unsupported_suggestion_rate':(answered-top3)/n,
            'mean_questions':questions/n, 'abstention_rate':abstained/n}


def verify(path):
    result = json.loads(Path(path).read_text())
    protocol = json.loads((ROOT/'experiments/policy_selection_protocol.json').read_text())
    assert result['protocol'] == protocol
    assert result['selected_operating_point'] is None and result['held_out_evaluated'] is False
    assert result['selection_only'] is True
    for relative, expected in protocol['input_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == expected
    for relative, expected in result['method_files_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == expected
    baseline = {c['case_id']:c for c in json.loads((ROOT/'experiments/results/decision_selection_2024_v2/selection_cases.json').read_text())}
    cohorts = {group:json.loads((ROOT/f'experiments/results/question_selection_2024_v2/{group}_cases.json').read_text())
               for group in ('all_attributes','structured_fields_only','coded_fields_only')}
    expected_keys = {(group, stratum, strategy, tau, gain)
                     for group, cases in cohorts.items()
                     for stratum in ['all',*sorted({c['part_change'] for c in cases})]
                     for strategy in ('information_gain','random','no_questions')
                     for tau in protocol['tau_answer_grid'] for gain in protocol['g_min_grid']}
    seen = set()
    for point in result['tables']:
        key = tuple(point[k] for k in ('cohort','stratum','strategy','tau_answer','g_min'))
        assert key not in seen and key in expected_keys
        seen.add(key)
        cases = cohorts[point['cohort']]
        if point['stratum'] != 'all':
            cases = [c for c in cases if c['part_change'] == point['stratum']]
        actual = independent(cases, baseline, point, protocol)
        for metric, value in actual.items():
            assert (point[metric] is None if value is None else math.isclose(point[metric],value,abs_tol=1e-12)), (key,metric)
        for metric, interval in point['ci95'].items():
            count = interval['valid_resamples']
            assert 0 <= count <= protocol['bootstrap_resamples']
            if not count:
                assert interval['low'] is interval['high'] is None
                assert metric.startswith('accuracy_') and point['n_answered'] == 0
            else:
                assert 0 <= interval['low'] <= interval['high'] <= (3 if metric == 'mean_questions' else 1)
    assert seen == expected_keys
    summary = {'independent_stopping_metrics':'PASS','rows_verified':len(seen),
               'n_pairs':protocol['n_pairs'],'n_originals':protocol['n_originals'],
               'year':2024,'held_out_2025_read':False,'operating_point_selected':False,
               'selection_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    print(json.dumps(summary,indent=2))
    return summary


if __name__ == '__main__':
    verify(sys.argv[1])
