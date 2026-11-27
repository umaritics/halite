"""Replay frozen 2024 question prefixes through the actual stopping rule."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess

from investigation.beliefs import entropy, load_parameters, score_beliefs
from investigation.experiments.simulated_technician import POLICIES, score_trace
from investigation.policy import PolicyParameters, decide

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ('all_attributes', 'structured_fields_only', 'coded_fields_only')
METRICS = ('coverage', 'accuracy_top1', 'accuracy_top3',
           'unsupported_suggestion_rate', 'mean_questions', 'abstention_rate')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stop_prefix(hypotheses, trace, parameters):
    """No answer key is available on this decision path. Stable named-rank ties."""
    names = [h['part_name'] for h in hypotheses]
    if len(names) != len(set(names)) or len(trace) != parameters.max_questions + 1:
        raise ValueError('Inconsistent hypothesis basis or question trace length.')
    history = []
    for index, step in enumerate(trace):
        values = step['beliefs']
        if len(values) != len(names) + 1:
            raise ValueError('Trace beliefs do not match the named basis plus other.')
        entropy(values)
        if not index and (step['questions_asked'] != 0 or step['attribute'] is not None):
            raise ValueError('A question trace must start before any answer.')
        if index:
            previous = trace[index - 1]
            if step['questions_asked'] == previous['questions_asked']:
                if values != previous['beliefs'] or step['attribute'] is not None or step['gain_bits'] is not None:
                    raise ValueError('A padded trace must preserve beliefs without another question.')
            elif step['questions_asked'] != previous['questions_asked'] + 1 or step['attribute'] is None:
                raise ValueError('An applied question must advance the count by one.')
        order = sorted(range(len(names)), key=lambda i: (-values[i], i))
        beliefs = {'hypotheses': [{**hypotheses[i], 'belief': values[i]} for i in order],
                   'other': values[-1], 'calibrated': True}
        following = trace[index + 1] if index + 1 < len(trace) else None
        question = None
        if following and following['attribute'] is not None and following['questions_asked'] > step['questions_asked']:
            if following['questions_asked'] != step['questions_asked'] + 1:
                raise ValueError('Question counts must advance by exactly one.')
            question = {'attribute': following['attribute'], 'gain_bits': following['gain_bits']}
        choice = decide(beliefs, parameters=parameters,
                        questions_asked=step['questions_asked'], best_question=question)
        history.append({'step': index, 'decision': choice['decision'], **choice['policy_inputs']})
        if choice['decision'] != 'ask':
            return {'decision': choice['decision'], 'questions_asked': step['questions_asked'],
                    'named_order': [names[i] for i in order], 'beliefs': list(values),
                    'history': history}
    raise ValueError('Trace ended while the policy still requested an answer.')


def score_outcome(stopped, answer_part):
    """The downstream correction key cannot change stopping, questions or beliefs."""
    named = stopped['named_order']
    answered = stopped['decision'] == 'answer'
    top1, top3 = bool(named) and named[0] == answer_part, answer_part in named[:3]
    # Additive sufficient statistics allow exact cluster-bootstrap weighting.
    return [1, int(answered), int(answered and top1), int(answered and top3),
            stopped['questions_asked'], int(not answered)]


def metrics(totals):
    n, answered, top1, top3, questions, abstained = map(float, totals)
    return {'coverage': answered / n, 'accuracy_top1': top1 / answered if answered else None,
            'accuracy_top3': top3 / answered if answered else None,
            'unsupported_suggestion_rate': (answered - top3) / n,
            'mean_questions': questions / n, 'abstention_rate': abstained / n}


def cluster_weights(query_ids, *, seed, resamples):
    """Same original-report draw is used for every threshold and strategy."""
    import numpy as np
    if type(resamples) is not int or resamples < 1 or not query_ids:
        raise ValueError('Nonempty originals and positive bootstrap count required.')
    rng = random.Random(seed)
    weights = np.zeros((resamples, len(query_ids)), dtype=np.int32)
    for row in weights:
        for _ in query_ids:
            row[rng.randrange(len(query_ids))] += 1
    return weights


def summarize(rows, query_ids, *, weights):
    import numpy as np
    groups = sorted(set(query_ids))
    if not rows or len(rows) != len(query_ids) or weights.shape[1] != len(groups):
        raise ValueError('Rows, originals and bootstrap weights are inconsistent.')
    grouped = np.zeros((len(groups), 6), dtype=np.float64)
    positions = {qid: i for i, qid in enumerate(groups)}
    for qid, row in zip(query_ids, rows):
        grouped[positions[qid]] += row
    total = grouped.sum(axis=0)
    draws = weights @ grouped
    n, answered, top1, top3, questions, abstained = draws.T
    safe = lambda values: np.divide(values, answered, out=np.full_like(answered, np.nan), where=answered > 0)
    values = [answered/n, safe(top1), safe(top3), (answered-top3)/n, questions/n, abstained/n]
    intervals = {}
    for key, draws_for_key in zip(METRICS, values):
        valid = draws_for_key[np.isfinite(draws_for_key)]
        bounds = np.percentile(valid, [2.5, 97.5]) if len(valid) else [None, None]
        intervals[key] = {'low': None if bounds[0] is None else float(bounds[0]),
                          'high': None if bounds[1] is None else float(bounds[1]),
                          'valid_resamples': len(valid)}
    return {'n_pairs': int(total[0]), 'n_originals': len(groups), 'n_answered': int(total[1]),
            'n_correct_top1': int(total[2]), 'n_correct_top3': int(total[3]),
            **metrics(total), 'ci95': intervals}


def load_inputs(root=ROOT, protocol=None):
    root = Path(root).resolve()
    protocol = protocol or json.loads((root/'experiments/policy_selection_protocol.json').read_text())
    if protocol['year'] != 2024 or protocol['fit_years'] != [2023] or protocol['held_out_evaluated']:
        raise ValueError('Selection accepts frozen 2023-fit / 2024 traces only.')
    for relative, expected in protocol['input_sha256'].items():
        path = (root/relative).resolve()
        if not path.is_relative_to(root) or sha(path) != expected:
            raise ValueError('Frozen selection input fingerprint mismatch: ' + relative)
    baseline = root/'experiments/results/decision_selection_2024_v2'
    question = root/'experiments/results/question_selection_2024_v2'
    selection = json.loads((baseline/'selection.json').read_text())
    result = json.loads((question/'results.json').read_text())
    for relative, expected in result['method_files_sha256'].items():
        if sha(root.parent/relative) != expected:
            raise ValueError('Frozen question-generation method changed: ' + relative)
    parameters = load_parameters(root/'params/mid_heuristic-v1.json', ranker_version=selection['ranker_version'])
    if parameters.as_dict() != selection['fit']['parameters'] or result['parameters'] != parameters.as_dict():
        raise ValueError('Question and ranking fit parameters disagree.')
    if result['held_out_evaluated'] or selection['held_out_evaluated'] or result['year'] != 2024:
        raise ValueError('Held-out evaluation is not a selection input.')
    baseline_cases = json.loads((baseline/'selection_cases.json').read_text())
    cases = {c['case_id']: c for c in baseline_cases}
    if len(cases) != protocol['n_pairs'] or len({c['query_id'] for c in cases.values()}) != protocol['n_originals']:
        raise ValueError('Unexpected selection denominators.')
    cohorts = {}
    for group in GROUPS:
        rows = json.loads((question/(group+'_cases.json')).read_text())
        if len(rows) != len(cases) or {c['case_id'] for c in rows} != cases.keys():
            raise ValueError('Question cohort differs from the frozen ranking cases.')
        for row in rows:
            base = cases[row['case_id']]
            beliefs = score_beliefs(base['hypotheses'], ranker_version=base['ranker_version'], parameters=parameters)
            if (base['year'] != 2024 or row['query_id'] != base['query_id'] or
                row['answer_part'] != base['answer_part'] or row['part_change'] != base['part_change'] or
                row['names'] != [h['part_name'] for h in beliefs['hypotheses']]):
                raise ValueError('Question case identity, basis or scoring key changed.')
            for strategy in POLICIES:
                trace = row['traces'][strategy]
                initial = [h['belief'] for h in beliefs['hypotheses']] + [beliefs['other']]
                # Recomputed exp/log values can differ by an ULP across Python
                # platforms. Saved trace bytes stay exact and remain authoritative.
                saved = trace[0]['beliefs']
                if len(saved) != len(initial) or not all(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14) for a, b in zip(saved, initial)):
                    raise ValueError('Question prior changed: ' + row['case_id'])
                if score_trace(trace, row['names'], row['answer_part']) != row['metrics'][strategy]:
                    raise ValueError('Saved downstream metrics changed: ' + row['case_id'])
            row['hypotheses'] = beliefs['hypotheses']
        cohorts[group] = rows
    return protocol, cohorts


def run(output, *, root=ROOT, protocol=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Preserve previous selection evidence; choose a fresh output directory.')
    protocol, cohorts = load_inputs(root, protocol)
    if protocol['n_min'] != 2 or protocol['max_questions'] != 3:
        raise ValueError('Selection must preserve the runtime evidence and question budgets.')
    grid = [PolicyParameters(tau, gain, protocol['n_min'], protocol['max_questions'])
            for tau in protocol['tau_answer_grid'] for gain in protocol['g_min_grid']]
    tables = []
    for group, cases in cohorts.items():
        strata = {'all': cases, **{key: [c for c in cases if c['part_change'] == key]
                                  for key in sorted({c['part_change'] for c in cases})}}
        for stratum, rows in strata.items():
            queries = [c['query_id'] for c in rows]
            weights = cluster_weights(sorted(set(queries)), seed=protocol['seed'], resamples=protocol['bootstrap_resamples'])
            for strategy in POLICIES:
                for point in grid:
                    stopped = [stop_prefix(c['hypotheses'], c['traces'][strategy], point) for c in rows]
                    scored = [score_outcome(state, c['answer_part']) for state, c in zip(stopped, rows)]
                    fingerprint = hashlib.sha256(json.dumps(stopped, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                    tables.append({'cohort': group, 'stratum': stratum, 'strategy': strategy,
                                   'tau_answer': point.tau_answer, 'g_min': point.g_min,
                                   'stopped_states_sha256': fingerprint, **summarize(scored, queries, weights=weights)})
        print('Completed stopping comparison: ' + group, flush=True)
    method_paths = [Path(__file__), ROOT/'beliefs.py', ROOT/'policy.py', ROOT/'experiments/abstention_curve.py']
    result = {'method_version': 'question-conditioned-selection-v1', 'protocol': protocol,
              'method_files_sha256': {str(p.relative_to(ROOT)): sha(p) for p in method_paths},
              'git_commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'working_tree_dirty': bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
              'interval': '95% percentile bootstrap by original report; undefined answered accuracy retains null and valid-resample count.',
              'selection_only': True, 'held_out_evaluated': False, 'selected_operating_point': None,
              'unsupported_definition': 'Answered cases whose correction part is outside the terminal top three, divided by all cases; outcome-key proxy, not sentence hallucination.',
              'question_burden_definition': 'Mean applied questions over all cases, including eventual abstentions.',
              'tables': tables}
    output.mkdir(parents=True)
    (output/'selection.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    columns = ['cohort','stratum','strategy','tau_answer','g_min','n_answered','coverage','accuracy_top1','accuracy_top3','unsupported_suggestion_rate','mean_questions']
    import csv
    with (output/'selection.csv').open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore'); writer.writeheader(); writer.writerows(tables)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({'rows':len(result['tables']), 'year':2024, 'selected_operating_point':None}))
