"""Reproduce selection maths from committed score cases, without FAA/network/graph/model access."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'backend'))
from investigation.beliefs import load_parameters
from investigation.experiments.abstention_curve import abstention_curve, evaluate_cases
from investigation.experiments.calibration import fit_parameters


def main():
    root = REPO / 'backend/investigation/experiments'
    output = root / 'results/decision_selection_2024_v2'
    result = json.loads((output / 'selection.json').read_text())
    digest = hashlib.sha256()
    # Precise dependencies of the frozen v2 baseline. New unrelated experiment
    # modules must not invalidate an unchanged baseline method fingerprint.
    files = [root / n for n in ('__init__.py', 'abstention_curve.py', 'calibration.py',
                                'decision_benchmark.py', 'download_projection.py', 'offline.py')] + [root.parent / n for n in ('beliefs.py', 'policy.py', 'ranker_port.py')]
    for path in files:
        digest.update(path.name.encode() + b'\0' + path.read_bytes())
    assert digest.hexdigest() == result['method_source_sha256'], 'Method source has changed; do not silently reuse this result.'
    fit_cases = json.loads((output / 'fit_cases.json').read_text())
    selection_cases = json.loads((output / 'selection_cases.json').read_text())
    fitted = fit_parameters(fit_cases, ranker_version=result['ranker_version'], corpus_sha256=result['fit_corpus']['corpus_sha256'])
    assert fitted == result['fit'], 'Fitted parameters/optimizer output differ.'
    parameters = load_parameters(root.parent / 'params/mid_heuristic-v1.json', ranker_version=result['ranker_version'])
    assert parameters.as_dict() == fitted['parameters']
    evaluated = evaluate_cases(selection_cases, ranker_version=result['ranker_version'], parameters=parameters)
    actual = abstention_curve(evaluated, thresholds=[r['tau_answer'] for r in result['selection']['curve']],
                              seed=result['selection']['seed'], resamples=result['selection']['bootstrap_resamples'])
    assert actual == result['selection'], 'Selection metrics/intervals differ.'
    for category, expected in result['by_part_change'].items():
        actual = abstention_curve([r for r in evaluated if r['part_change'] == category], thresholds=[r['tau_answer'] for r in expected['curve']],
                                 seed=expected['seed'], resamples=expected['bootstrap_resamples'])
        assert actual == expected, f'Stratified result differs: {category}'
    errors = {'n_pairs': len(selection_cases), 'n_originals': len({c['query_id'] for c in selection_cases}),
              'empty_ranking': 0, 'true_part_missing_top10': 0, 'true_part_missing_top3': 0,
              'leading_hypothesis_fewer_than_two_records': 0, 'by_part_change': {}, 'examples': []}
    for case in selection_cases:
        names = [h['part_name'].strip().upper() for h in case['hypotheses']]
        target = case['answer_part'].strip().upper()
        errors['empty_ranking'] += not bool(names)
        errors['true_part_missing_top10'] += target not in names
        errors['true_part_missing_top3'] += target not in names[:3]
        errors['leading_hypothesis_fewer_than_two_records'] += (not names or case['hypotheses'][0]['evidence_count'] < 2)
        group = errors['by_part_change'].setdefault(case['part_change'], Counter())
        group['n'] += 1
        group['missing_top10'] += target not in names
        group['correct_top1'] += bool(names) and names[0] == target
        group['correct_top3'] += target in names[:3]
        if target not in names[:3] and len(errors['examples']) < 5:
            errors['examples'].append({'case_id': case['case_id'], 'answer_part': target, 'ranked_top3': names[:3], 'category': case['part_change']})
    proof = {'method_fingerprint_equal': True, 'fit_reproduced_exactly': True, 'selection_and_all_intervals_reproduced_exactly': True,
             'stratified_results_reproduced_exactly': True, 'network_graph_model_calls': 0, 'held_out_evaluated': False,
             'error_analysis': errors}
    print(json.dumps(proof, indent=2))
    print('DECISION_SELECTION_REPLAY=PASS')


if __name__ == '__main__':
    main()
