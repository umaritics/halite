"""Question-policy comparison. Simulated answers come only from the original report."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time

from investigation.attributes import CODED, CUES, NOT_SURE, fit_schema, load_codebook
from investigation.beliefs import entropy, load_parameters, score_beliefs
from investigation.experiments.abstention_curve import _interval
from investigation.experiments.offline import Corpus, load_records
from investigation.experiments.temporal_questions import TemporalQuestionIndex
from investigation.questions import answer_question, select_question

POLICIES = ('information_gain', 'random', 'no_questions')


def simulate(initial, models, original_values, *, codebook, strategy, query_id, seed=1729, max_questions=3):
    """No correction/answer-key argument exists on the question/answer path."""
    if strategy not in POLICIES or type(max_questions) is not int or max_questions < 0:
        raise ValueError('Invalid simulation policy or question budget.')
    entropy(initial)
    prior, excluded = list(initial), set()
    local_seed = int.from_bytes(hashlib.sha256(f'{seed}:{query_id}'.encode()).digest()[:8], 'big')
    rng = random.Random(local_seed)
    trace = [{'beliefs': list(prior), 'entropy': entropy(prior), 'attribute': None, 'answer': None, 'gain_bits': None, 'questions_asked': 0}]
    asked = 0
    for _ in range(max_questions):
        question = None if strategy == 'no_questions' else select_question(prior, models, excluded=excluded, codebook=codebook, strategy=strategy, rng=rng)
        value = None
        if question:
            attribute = question['attribute']
            value = original_values.get(attribute, NOT_SURE)
            if value not in {o['value'] for o in question['options']}:
                value = NOT_SURE  # Unseen/not-offered values are not invented answers.
            prior = answer_question(prior, question, value)
            excluded.add(attribute)  # Includes not_sure: never ask the same attribute again.
            asked += 1
        trace.append({'beliefs': list(prior), 'entropy': entropy(prior),
                      'attribute': question['attribute'] if question else None, 'answer': value,
                      'gain_bits': question['gain_bits'] if question else None, 'questions_asked': asked})
    return trace


def score_trace(trace, names, answer_part):
    # Evaluation is downstream of simulation, and cannot alter questions/answers.
    result = []
    for step in trace:
        order = sorted(range(len(names)), key=lambda i: (-step['beliefs'][i], i))
        ranked = [names[i] for i in order]
        result.append({'top1': float(bool(ranked) and ranked[0] == answer_part),
                       'top3': float(answer_part in ranked[:3]), 'entropy': step['entropy'],
                       'questions_asked': step['questions_asked']})
    return result


def summarize(cases, *, seed=1729, resamples=1000):
    if not cases or resamples < 1:
        raise ValueError('Nonempty cases and positive bootstrap count are required.')
    groups = {}
    for case in cases:
        groups.setdefault(case['query_id'], []).append(case)
    grouped = list(groups.values())
    keys = ('top1', 'top3', 'entropy', 'questions_asked')
    def means(rows):
        return {policy: [{key: sum(c['metrics'][policy][step][key] for c in rows) / len(rows) for key in keys}
                         for step in range(4)] for policy in POLICIES}
    values = means(cases)
    draws = {policy: [{key: [] for key in keys} for _ in range(4)] for policy in POLICIES}
    differences = [{key: [] for key in ('top1', 'top3', 'entropy')} for _ in range(4)]
    rng = random.Random(seed)
    for _ in range(resamples):
        sampled = [case for _ in grouped for case in grouped[rng.randrange(len(grouped))]]
        boot = means(sampled)
        for policy in POLICIES:
            for step in range(4):
                for key in keys:
                    draws[policy][step][key].append(boot[policy][step][key])
        for step in range(4):
            for key in differences[step]:
                differences[step][key].append(boot['information_gain'][step][key] - boot['random'][step][key])
    return {'n_pairs': len(cases), 'n_originals': len(groups), 'bootstrap_resamples': resamples, 'seed': seed,
            'interval': '95% percentile cluster bootstrap by original report; paired policy differences',
            'policies': {policy: [{'after_questions': step, **v, 'ci95': {key: _interval(draws[policy][step][key]) for key in keys}}
                                  for step, v in enumerate(values[policy])] for policy in POLICIES},
            'information_gain_minus_random': [{'after_questions': step,
                **{key: values['information_gain'][step][key] - values['random'][step][key] for key in differences[step]},
                'ci95': {key: _interval(draw) for key, draw in differences[step].items()}} for step in range(4)]}


def run(*, sources, baseline_directory, output, resamples=1000, seed=1729):
    started = time.perf_counter()
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a fresh results directory; prior experiments must remain reviewable.')
    baseline = Path(baseline_directory)
    selection = json.loads((baseline / 'selection.json').read_text())
    score_cases = json.loads((baseline / 'selection_cases.json').read_text())
    if selection['held_out_evaluated'] or any(c['year'] != 2024 or c['ranker_version'] != selection['ranker_version'] for c in score_cases):
        raise ValueError('This preparation compares policies on 2024 selection only.')
    records, meta = load_records(sources)
    if any(r['year'] not in (2023, 2024) for r in records.values()) or meta['corpus_sha256'] != selection['selection_corpus']['corpus_sha256']:
        raise ValueError('Expected the exact frozen 2023/2024 source projections.')
    corpus = Corpus(records)
    book = load_codebook()
    schema = fit_schema([r for r in records.values() if r['year'] == 2023], corpus_sha256=selection['fit_corpus']['corpus_sha256'], codebook=book)
    index = TemporalQuestionIndex(corpus, schema)
    parameters = load_parameters(baseline.parent.parent.parent / 'params/mid_heuristic-v1.json', ranker_version=selection['ranker_version'])
    if parameters.as_dict() != selection['fit']['parameters']:
        raise ValueError('Frozen 2023 calibration parameters differ.')
    sets = {'all_attributes': set(schema['domains']),
            'structured_fields_only': set(CODED) | {'part_condition', 'location_zone'},
            'coded_fields_only': set(CODED)}
    results = {name: [] for name in sets}
    cache = {}
    for number, case in enumerate(sorted(score_cases, key=lambda c: (records[c['query_id']]['submitted_at'], c['query_id'], c['case_id']))):
        query_id = case['query_id']
        if query_id not in cache:
            beliefs = score_beliefs(case['hypotheses'], ranker_version=case['ranker_version'], parameters=parameters)
            names = [h['part_name'] for h in beliefs['hypotheses']]
            prior = [h['belief'] for h in beliefs['hypotheses']] + [beliefs['other']]
            models, audit = index.for_query(query_id, names)
            cache[query_id] = {'names': names, 'hypotheses': case['hypotheses'], 'audit': audit, 'traces': {}}
            for name, attributes in sets.items():
                subset = {key: value for key, value in models.items() if key in attributes}
                cache[query_id]['traces'][name] = {policy: simulate(prior, subset, index.values[query_id], codebook=book,
                    strategy=policy, query_id=query_id, seed=seed) for policy in POLICIES}
        saved = cache[query_id]
        if saved['hypotheses'] != case['hypotheses']:
            raise ValueError('Repeated original has inconsistent initial ranking.')
        for name in sets:
            traces = saved['traces'][name]
            results[name].append({'case_id': case['case_id'], 'query_id': query_id, 'part_change': case['part_change'],
                                  'answer_part': case['answer_part'], 'names': saved['names'], 'audit': saved['audit'],
                                  'traces': traces, 'metrics': {p: score_trace(t, saved['names'], case['answer_part']) for p,t in traces.items()}})
        if number % 100 == 0:
            print(f'Simulated {number+1}/{len(score_cases)} pairs', flush=True)
    summaries = {name: {'all': summarize(cases, seed=seed, resamples=resamples),
                        'by_part_change': {category: summarize([c for c in cases if c['part_change'] == category], seed=seed, resamples=resamples)
                                           for category in sorted({c['part_change'] for c in cases})}}
                 for name,cases in results.items()}
    sources_used = [Path(__file__), Path(__file__).with_name('temporal_questions.py'), Path(__file__).with_name('offline.py'), Path(__file__).with_name('abstention_curve.py'),
                    *[Path(__file__).parent.parent / n for n in ('attributes.py','questions.py','beliefs.py','ranker_port.py')]]
    source_hashes = {str(p.relative_to(Path(__file__).parents[2])): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources_used}
    output.mkdir(parents=True)
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    result = {'method_version':'question-selection-v2', 'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
              'method_files_sha256': source_hashes, 'corpus':meta, 'year':2024, 'held_out_evaluated':False,
              'ranker_version':selection['ranker_version'], 'baseline_score_cases_sha256':sha(baseline/'selection_cases.json'),
              'schema':schema, 'codebook':{'source':book['source'],'archive_sha256':book['archive_sha256']},
              'parameters':parameters.as_dict(), 'summaries':summaries,
              'asked_attributes':{name:{policy:dict(Counter(step['attribute'] for c in cases for step in c['traces'][policy] if step['attribute'])) for policy in POLICIES} for name,cases in results.items()},
              'not_sure_answers':{name:{policy:sum(step['answer']==NOT_SURE for c in cases for step in c['traces'][policy]) for policy in POLICIES} for name,cases in results.items()},
              'elapsed_seconds':time.perf_counter()-started,
              'notes':['Original-report attributes only supply simulated answers; correction part is evaluation only.',
                       'Every likelihood count uses strictly earlier submissions and excludes the full query citation chain.',
                       'Narrative cues measure mention, including negative findings. All-attribute gains are structured reuse of initial narrative, not new observations.',
                       'Structured-only (six attributes) and coded-only (four) controls separate narrative reuse and question-pool composition.',
                       'Three-question budget is an experimental comparison; no production gain/answer threshold is selected.',
                       'Unknown correction outcome keys remain excluded as in the frozen baseline. No 2025 file was read.']}
    (output/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    for name,cases in results.items():
        (output/(name+'_cases.json')).write_text('[\n'+',\n'.join(json.dumps(c,separators=(',',':'),ensure_ascii=False,allow_nan=False) for c in cases)+'\n]\n')
    n_pairs = summaries['all_attributes']['all']['n_pairs']
    n_originals = summaries['all_attributes']['all']['n_originals']
    lines=['# 2024 simulated-technician selection','',f'{n_pairs} correction pairs, {n_originals} original reports. Frozen Mid-I ranking and 2023-fitted beliefs. 2025 remains held out.','',
           'Every answer comes from the original report. Coded-only separates structured fields from narrative-mention reuse. Intervals and paired differences are in `results.json`.','']
    for name,summary in summaries.items():
        lines += ['## '+name.replace('_',' '),'','| Policy | After questions | Top-1 accuracy | Top-3 accuracy | Mean entropy (bits) |','| --- | --- | --- | --- | --- |']
        for policy,steps in summary['all']['policies'].items():
            for step in steps:lines.append(f"| {policy} | {step['after_questions']} | {step['top1']:.4f} | {step['top3']:.4f} | {step['entropy']:.4f} |")
        lines.append('')
    (output/'QUESTION_TABLE.md').write_text('\n'.join(lines)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',nargs='+',required=True)
    parser.add_argument('--baseline-directory',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--bootstrap',type=int,default=1000)
    args=parser.parse_args()
    result=run(sources=args.sources,baseline_directory=args.baseline_directory,output=args.output,resamples=args.bootstrap)
    print(json.dumps({'elapsed_seconds':result['elapsed_seconds'],'n_pairs':result['summaries']['all_attributes']['all']['n_pairs']},indent=2))
