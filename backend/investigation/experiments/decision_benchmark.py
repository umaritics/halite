"""Fit 2023 and produce a 2024 selection table. Held-out evaluation is separate."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time

from investigation.beliefs import BeliefParameters
from investigation.experiments.offline import Corpus, load_records, ranked_cases, UNKNOWN
from investigation.experiments.calibration import fit_parameters
from investigation.experiments.abstention_curve import abstention_curve, evaluate_cases
from investigation.ranker_port import MID_VERSION


def run(fit_corpus, selection_corpus, output, *, resamples=1000, seed=1729):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a fresh output directory to preserve previous experiments.')
    started = time.perf_counter()
    records, fit_meta = load_records(fit_corpus)
    if any(r['year'] != 2023 for r in records.values()):
        raise ValueError('Fit sources must contain 2023 occurrence-year records only.')
    corpus = Corpus(records)
    fit_cases = ranked_cases(corpus, 2023)
    print(f'Ranked {len(fit_cases)} fit cases', flush=True)
    fit = fit_parameters(fit_cases, ranker_version=MID_VERSION, corpus_sha256=fit_meta['corpus_sha256'])
    p = fit['parameters']
    parameters = BeliefParameters(p['ranker_version'], p['temperature'], p['other_score'], tuple(p['fit_years']), p['corpus_sha256'])
    records, select_meta = load_records([*fit_corpus, *selection_corpus])
    if any(r['year'] not in (2023, 2024) for r in records.values()):
        raise ValueError('Selection must not include held-out occurrence years.')
    selection = Corpus(records)
    select_cases = ranked_cases(selection, 2024)
    print(f'Ranked {len(select_cases)} selection cases', flush=True)
    evaluated = evaluate_cases(select_cases, ranker_version=MID_VERSION, parameters=parameters)
    curve = abstention_curve(evaluated, thresholds=[i / 20 for i in range(21)], seed=seed, resamples=resamples)
    methods = sorted(Path(__file__).parent.glob('*.py')) + [Path(__file__).parent.parent / n for n in ('beliefs.py', 'policy.py', 'ranker_port.py')]
    method_sha = hashlib.sha256()
    for path in methods:
        method_sha.update(path.name.encode() + b'\0' + path.read_bytes())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip())
    result = {'method_version': 'mid-beliefs-selection-v2', 'method_source_sha256': method_sha.hexdigest(),
              'git_commit': commit, 'working_tree_dirty': dirty, 'ranker_version': MID_VERSION,
              'split': {'fit': [2023], 'select': [2024], 'test': [2025]}, 'held_out_evaluated': False,
              'fit_corpus': fit_meta, 'selection_corpus': select_meta, 'fit': fit,
              'case_protocol': 'Explicit FAA same-tail forward-submission correction pairs; original text as query; known named correction part as answer key; exclude full query chain and all non-earlier submissions.',
              'fit_pair_discards': corpus.discards, 'selection_pair_discards': selection.discards,
              'fit_valid_pairs': len(corpus.pairs),
              'fit_unknown_outcome_excluded': sum(corpus.records[n]['part_name'] in UNKNOWN for o, n in corpus.pairs if corpus.records[o]['year'] == 2023),
              'selection_unknown_outcome_excluded': sum(selection.records[n]['part_name'] in UNKNOWN for o, n in selection.pairs if selection.records[o]['year'] == 2024), 'selection_all_years_valid_pairs': len(selection.pairs),
              'fit_part_change': dict(Counter(c['part_change'] for c in fit_cases)),
              'selection_part_change': dict(Counter(c['part_change'] for c in select_cases)),
              'selection': curve,
              'by_part_change': {category: abstention_curve([r for r in evaluated if r['part_change'] == category], thresholds=[0, .5, 1], seed=seed, resamples=resamples)
                                 for category in sorted({r['part_change'] for r in evaluated})},
              'elapsed_seconds': time.perf_counter() - started,
              'notes': ['This evaluates the bounded Mid-I heuristic, not a trained diagnostic model.',
                        'Exact named-part keys are a proxy; no fault-cause/airworthiness claim.',
                        'Unknown/empty correction part keys are excluded from accuracy calibration, not relabelled as known causes.',
                        'All known-outcome correction pairs are retained; bootstrap clusters pairs sharing an original report.',
                        'Offline occurrence-date ties use record ID descending for deterministic input order; live Mid-I ties have no secondary Cypher key.',
                        'Operating point is unselected. 2025 remains untouched.']}
    output.mkdir(parents=True)
    for name, data in [('selection.json', result), ('fit_cases.json', fit_cases), ('selection_cases.json', select_cases), ('parameters.json', p)]:
        (output / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    lines = ['# 2024 operating-point selection', '', f'Ranker: `{MID_VERSION}`. Fit: {len(fit_cases)} cases (2023). Selection: {len(select_cases)} cases (2024).', '',
             'No operating point has been chosen; 2025 has not been evaluated.', '',
             '| Answer threshold | Cases answered | Coverage | Top-1 accuracy | Top-3 accuracy | Unsupported / all cases |',
             '| --- | --- | --- | --- | --- | --- |']
    def show(v):
        return '—' if v is None else f'{v:.4f}'
    for row in curve['curve']:
        lines.append('| ' + ' | '.join([show(row['tau_answer']), str(row['n_answered']), *[show(row[k]) for k in ('coverage','accuracy_top1','accuracy_top3','unsupported_suggestion_rate')]]) + ' |')
    lines += ['', 'All intervals, seed, fingerprints, pair exclusions and source provenance are in `selection.json`.',
              'Bars remain relative support. Results may be poor; selection does not establish test performance.']
    (output / 'SELECTION_TABLE.md').write_text('\n'.join(lines) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fit-corpus', nargs='+', required=True)
    parser.add_argument('--selection-corpus', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--bootstrap', type=int, default=1000)
    args = parser.parse_args()
    result = run(args.fit_corpus, args.selection_corpus, args.output, resamples=args.bootstrap)
    print(json.dumps({'n_fit': result['fit']['n'], 'n_select': result['selection']['n'], 'elapsed_seconds': result['elapsed_seconds']}, indent=2))
