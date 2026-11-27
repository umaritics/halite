"""Accuracy/coverage, named-top calibration and deterministic bootstrap intervals."""
import math
import random
from investigation.beliefs import score_beliefs
from investigation.policy import PolicyParameters, decide


def evaluate_cases(cases, *, ranker_version, parameters):
    rows = []
    for case in cases:
        if case['ranker_version'] != ranker_version:
            raise ValueError('Ranker version mismatch in evaluation.')
        beliefs = score_beliefs(case['hypotheses'], ranker_version=ranker_version, parameters=parameters)
        names = [str(h['part_name']).strip().upper() for h in beliefs['hypotheses']]
        target = str(case['answer_part']).strip().upper()
        if not target:
            raise ValueError('An answer key is required.')
        rows.append({'case_id': case['case_id'], 'query_id': case.get('query_id', case['case_id']), 'year': case['year'], 'beliefs': beliefs,
                     'correct_top1': bool(names) and names[0] == target,
                     'correct_top3': target in names[:3], 'part_change': case.get('part_change', 'unknown')})
    return rows


def _metrics(rows, tau, n_min):
    policy = PolicyParameters(tau, 0, n_min=n_min)
    answered = [r for r in rows if decide(r['beliefs'], parameters=policy)['decision'] == 'answer']
    n = len(answered)
    return {'coverage': n / len(rows) if rows else None,
            'accuracy_top1': sum(r['correct_top1'] for r in answered) / n if n else None,
            'accuracy_top3': sum(r['correct_top3'] for r in answered) / n if n else None,
            'unsupported_suggestion_rate': sum(not r['correct_top3'] for r in answered) / len(rows) if rows else None,
            'n_answered': n, 'n_cases': len(rows)}


def abstention_off(rows):
    answered = [r for r in rows if r['beliefs']['hypotheses']]
    n = len(answered)
    return {'coverage': n / len(rows) if rows else None,
            'accuracy_top1': sum(r['correct_top1'] for r in answered) / n if n else None,
            'accuracy_top3': sum(r['correct_top3'] for r in answered) / n if n else None,
            'unsupported_suggestion_rate': sum(not r['correct_top3'] for r in answered) / len(rows) if rows else None,
            'n_answered': n, 'n_cases': len(rows)}


def expected_calibration_error(rows):
    if not rows:
        return None
    groups = [[] for _ in range(10)]
    for row in rows:
        top = row['beliefs']['hypotheses']
        confidence = top[0]['belief'] if top else 0.0
        groups[min(int(confidence * 10), 9)].append((confidence, row['correct_top1']))
    return sum(len(g) / len(rows) * abs(sum(p for p, _ in g) / len(g) - sum(y for _, y in g) / len(g)) for g in groups if g)


def _interval(values):
    valid = sorted(v for v in values if v is not None and math.isfinite(v))
    if not valid:
        return {'low': None, 'high': None, 'valid_resamples': 0}
    def percentile(p):
        index = (len(valid) - 1) * p
        lo = math.floor(index)
        return valid[lo] + (valid[math.ceil(index)] - valid[lo]) * (index - lo)
    return {'low': percentile(.025), 'high': percentile(.975), 'valid_resamples': len(valid)}


def abstention_curve(rows, *, thresholds, seed=1729, resamples=1000, n_min=2):
    if not rows or type(resamples) is not int or resamples < 1:
        raise ValueError('Nonempty evaluation and positive bootstrap count required.')
    thresholds = sorted(set(float(t) for t in thresholds))
    for t in thresholds:
        PolicyParameters(t, 0, n_min=n_min)
    metrics = [_metrics(rows, t, n_min) for t in thresholds]
    draws = [{key: [] for key in ('coverage', 'accuracy_top1', 'accuracy_top3', 'unsupported_suggestion_rate')} for _ in thresholds]
    eces = []
    off_draws = {key: [] for key in ('coverage', 'accuracy_top1', 'accuracy_top3', 'unsupported_suggestion_rate')}
    rng = random.Random(seed)
    clusters = {}
    for row in rows:
        clusters.setdefault(row.get('query_id', row['case_id']), []).append(row)
    groups = list(clusters.values())
    for _ in range(resamples):
        sampled = [row for _ in groups for row in groups[rng.randrange(len(groups))]]
        eces.append(expected_calibration_error(sampled))
        off = abstention_off(sampled)
        for key in off_draws:
            off_draws[key].append(off[key])
        for t, draw in zip(thresholds, draws):
            values = _metrics(sampled, t, n_min)
            for key in draw:
                draw[key].append(values[key])
    return {'n': len(rows), 'seed': seed, 'bootstrap_resamples': resamples,
            'interval': '95% percentile cluster bootstrap by original report', 'n_original_reports': len(groups), 'n_min': n_min,
            'ece_named_top_10_bins': expected_calibration_error(rows), 'ece_ci95': _interval(eces),
            'ece_definition': 'Leading named belief versus exact named-part top-1 correctness; empty ranking confidence zero.',
            'curve': [{'tau_answer': t, **values, 'ci95': {key: _interval(draw[key]) for key in draw}}
                      for t, values, draw in zip(thresholds, metrics, draws)],
            'abstention_off': {**abstention_off(rows), 'ci95': {key: _interval(values) for key, values in off_draws.items()}},
            'baseline_definition': 'Answer every nonempty ranking, without confidence/evidence gates; empty rankings stay unanswered.',
            'selected_operating_point': None}
