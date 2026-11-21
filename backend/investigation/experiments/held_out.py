"""Fixed 2025 evaluation. Synthetic tests/preflight precede explicit hosted access."""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import urllib.request

from investigation.attributes import CODED, load_codebook
from investigation.beliefs import load_parameters, score_beliefs
from investigation.experiments.download_projection import COLUMNS, download
from investigation.experiments.frozen_policy import REPO, preflight_held_out, sha
from investigation.experiments.offline import Corpus, UNKNOWN, load_records, ranked_cases
from investigation.experiments.policy_selection import cluster_weights, score_outcome, stop_prefix, summarize as stopping_summary
from investigation.experiments.simulated_technician import POLICIES, score_trace, simulate, summarize
from investigation.experiments.temporal_questions import TemporalQuestionIndex
from investigation.policy import PolicyParameters

ROOT = REPO/'backend/investigation'
SOURCE_2025 = 'https://external.apic4e.faa.gov/sdrs/retrieve/SDR-2025.csv'


def preflight_procedure():
    proof = preflight_held_out()
    files = proof['protocol'].get('procedure_files_sha256', {})
    required = {'backend/investigation/experiments/held_out.py',
                'docs/work/usman/verify_held_out.py', '.github/workflows/held-out.yml'}
    if not required.issubset(files):
        raise ValueError('Freeze the complete evaluation procedure before held-out access.')
    for relative, expected in files.items():
        path = (REPO/relative).resolve()
        if not path.is_relative_to(REPO) or sha(path) != expected:
            raise ValueError('The pre-test procedure changed: '+relative)
    return proof


def download_test(destination):
    proof = preflight_procedure()  # Before even opening a response or a destination.
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Preserve the held-out source; never replace it.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    partial = destination.with_suffix(destination.suffix+'.partial')
    digest, count = hashlib.sha256(), 0
    try:
        request = urllib.request.Request(SOURCE_2025,headers={'User-Agent':'Halite-FYP-Research/1.0'})
        with urllib.request.urlopen(request,timeout=120) as response, io.TextIOWrapper(response,encoding='utf-8-sig',newline='') as stream, gzip.open(partial,'wt',encoding='utf-8',newline='') as output:
            accessed = datetime.now(timezone.utc).isoformat()
            reader = csv.DictReader(stream)
            if not set(COLUMNS).issubset(reader.fieldnames or []):
                raise ValueError('Held-out FAA response is missing frozen projection fields.')
            writer = csv.DictWriter(output,fieldnames=COLUMNS)
            writer.writeheader()
            for row in reader:
                projected = {key:row[key] for key in COLUMNS}
                digest.update((json.dumps(projected,ensure_ascii=False,separators=(',',':'))+'\n').encode())
                writer.writerow(projected)
                count += 1
        if not count:
            raise ValueError('Refuse an empty held-out response.')
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)
    metadata = {'source':SOURCE_2025,'year':2025,'n_rows':count,'columns':list(COLUMNS),
                'projection_sha256':digest.hexdigest(),'first_response_opened_at_utc':accessed,
                'policy_sha256_before_access':proof['policy']['file_sha256'],
                'protocol_sha256_before_access':proof['protocol_sha256'],
                'fingerprint_definition':'Canonical ordered projected-row JSON UTF-8, newline per row.'}
    destination.with_suffix(destination.suffix+'.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


def calibration(rows, weights):
    """All terminal cases; leading NAMED support, ten equal-width bins."""
    import numpy as np
    groups = sorted({r['query_id'] for r in rows})
    if not rows or weights.shape[1] != len(groups):
        raise ValueError('Calibration requires nonempty rows and matching original-report weights.')
    positions = {qid:i for i,qid in enumerate(groups)}
    counts = np.zeros((len(groups),31),dtype=np.float64)
    for row in rows:
        confidence, correct = row['confidence'], row['correct_top1']
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError('Named support must be finite and bounded.')
        index = min(int(confidence*10),9)
        counts[positions[row['query_id']],0] += 1
        counts[positions[row['query_id']],1+index] += 1
        counts[positions[row['query_id']],11+index] += confidence
        counts[positions[row['query_id']],21+index] += correct
    def ece(totals):
        return np.abs(totals[...,11:21]-totals[...,21:31]).sum(axis=-1)/totals[...,0]
    totals = counts.sum(axis=0)
    draws = ece(weights@counts)
    low, high = np.percentile(draws,[2.5,97.5])
    return {'value':float(ece(totals)),'ci95':{'low':float(low),'high':float(high),'valid_resamples':len(draws)},
            'bins':[{'bin':i,'n':int(totals[1+i]),'support_sum':float(totals[11+i]),
                     'correct_top1':int(totals[21+i])} for i in range(10)],
            'definition':'All terminal cases; named-top support versus exact part-key top-one correctness. Empty rankings: confidence zero and incorrect.'}


def terminal_calibration(case, stopped):
    named = stopped['named_order']
    return {'query_id':case['query_id'],'confidence':max(stopped['beliefs'][:-1],default=0),
            'correct_top1':bool(named) and named[0]==case['answer_part']}


def evaluate(corpus, policy, protocol):
    """No fit or threshold-search function is called on this path."""
    scores = ranked_cases(corpus,2025)
    if not scores:
        raise ValueError('No eligible known-outcome 2025 correction pairs.')
    params = load_parameters(ROOT/'params/mid_heuristic-v1.json',ranker_version=policy['ranker_version'])
    schema = json.loads((ROOT/'params/report-attributes-v1.json').read_text())
    book = load_codebook()
    index = TemporalQuestionIndex(corpus,schema)
    pools = {'all_attributes':set(schema['domains']),
             'structured_fields_only':set(CODED)|{'part_condition','location_zone'},
             'coded_fields_only':set(CODED)}
    cohorts = {pool:[] for pool in pools}
    cached = {}
    point = PolicyParameters(**policy['parameters'])
    cutoff = datetime.fromisoformat(protocol['sensitivity_label_cutoff'])
    for number,case in enumerate(sorted(scores,key=lambda c:(corpus.records[c['query_id']]['submitted_at'],c['query_id'],c['case_id']))):
        qid = case['query_id']
        if qid not in cached:
            beliefs = score_beliefs(case['hypotheses'],ranker_version=case['ranker_version'],parameters=params)
            names = [h['part_name'] for h in beliefs['hypotheses']]
            prior = [h['belief'] for h in beliefs['hypotheses']]+[beliefs['other']]
            models, audit = index.for_query(qid,names)
            cache = {'names':names,'hypotheses':beliefs['hypotheses'],'audit':audit,'traces':{},'original_hypotheses':case['hypotheses']}
            for pool,attributes in pools.items():
                subset = {k:v for k,v in models.items() if k in attributes}
                cache['traces'][pool] = {strategy:simulate(prior,subset,index.values[qid],codebook=book,
                    strategy=strategy,query_id=qid,seed=protocol['seed']) for strategy in POLICIES}
            cached[qid] = cache
        cache = cached[qid]
        if cache['original_hypotheses'] != case['hypotheses'] or case['ranker_version'] != policy['ranker_version']:
            raise ValueError('Repeated original ranking or frozen ranker changed.')
        for pool in pools:
            traces = cache['traces'][pool]
            stopped = {strategy:stop_prefix(cache['hypotheses'],trace,point) for strategy,trace in traces.items()}
            cohorts[pool].append({**case,'names':cache['names'],'hypotheses':cache['hypotheses'],
                'audit':cache['audit'],'traces':traces,'stopped':stopped,
                'after_selection_labels':corpus.records[qid]['submitted_at']>cutoff,
                'metrics':{strategy:score_trace(trace,cache['names'],case['answer_part']) for strategy,trace in traces.items()}})
        if number%100==0:
            print(f'Evaluated fixed held-out path {number+1}/{len(scores)}',flush=True)
    curves, stopping = {}, []
    for pool,cases in cohorts.items():
        curves[pool] = {}
        for availability in ('primary_all','after_selection_labels'):
            subset = cases if availability=='primary_all' else [c for c in cases if c['after_selection_labels']]
            categories = ['all',*sorted({c['part_change'] for c in cases})]
            for category in categories:
                rows = subset if category=='all' else [c for c in subset if c['part_change']==category]
                key = availability+'/'+category
                if not rows:
                    curves[pool][key] = {'status':'empty','n_pairs':0,'n_originals':0}
                    continue
                curves[pool][key] = summarize(rows,seed=protocol['seed'],resamples=protocol['bootstrap_resamples'])
                queries = [c['query_id'] for c in rows]
                weights = cluster_weights(sorted(set(queries)),seed=protocol['seed'],resamples=protocol['bootstrap_resamples'])
                for strategy in POLICIES:
                    chosen = [c['stopped'][strategy] for c in rows]
                    # Counterfactual changes only the final answer gates. Identical
                    # final beliefs/questions isolate abstention from question policy.
                    off = [{**s,'decision':'answer' if s['named_order'] else 'abstain'} for s in chosen]
                    stopping.append({'cohort':pool,'availability':availability,'stratum':category,'strategy':strategy,
                        'chosen':stopping_summary([score_outcome(s,c['answer_part']) for c,s in zip(rows,chosen)],queries,weights=weights),
                        'abstention_off':stopping_summary([score_outcome(s,c['answer_part']) for c,s in zip(rows,off)],queries,weights=weights),
                        'named_top_ece':calibration([terminal_calibration(c,s) for c,s in zip(rows,chosen)],weights)})
    by_original = {c['query_id']:c for c in scores}
    return {'cohorts':cohorts,'question_budget_summaries':curves,'stopping':stopping,
        'case_counts':{'n_pairs':len(scores),'n_originals':len(by_original),
            'before_or_at_selection_label_time_pairs':sum(not c['after_selection_labels'] for c in cohorts['all_attributes']),
            'unknown_outcome_pairs_excluded':sum(corpus.records[a]['year']==2025 and corpus.records[b]['part_name'] in UNKNOWN for a,b in corpus.pairs),
            'pair_discards':corpus.discards,
            'true_part_missing_top10':sum(c['answer_part'] not in [h['part_name'] for h in c['hypotheses']] for c in scores)}}


def run(data_directory, output, *, allow_download=False):
    proof = preflight_procedure()
    data, output = Path(data_directory),Path(output)
    if output.exists():
        raise FileExistsError('Preserve the original held-out run; use a fresh evidence directory.')
    data.mkdir(parents=True,exist_ok=True)
    baseline = json.loads((ROOT/'experiments/results/decision_selection_2024_v2/selection.json').read_text())
    history = [data/f'usman_decision_{year}.csv.gz' for year in (2023,2024)]
    for year,path in zip((2023,2024),history):
        if not path.exists():
            if not allow_download:raise FileNotFoundError('Frozen history projection is missing.')
            download(year,path)
    _,history_meta = load_records(history)
    if history_meta['corpus_sha256'] != baseline['selection_corpus']['corpus_sha256']:
        raise ValueError('Historical FAA projections changed; do not open held-out data.')
    del _
    output.mkdir(parents=True)
    receipt = {'recorded_before_test_access_utc':datetime.now(timezone.utc).isoformat(),
               'policy_sha256':proof['policy']['file_sha256'],'protocol_sha256':proof['protocol_sha256'],
               'procedure_files_sha256':proof['protocol']['procedure_files_sha256'],
               'history_corpus_sha256':history_meta['corpus_sha256'],'parameters':proof['policy']['parameters'],
               'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}
    (output/'pretest-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    test = data/'usman_decision_2025.csv.gz'
    if not test.exists():
        if not allow_download:raise FileNotFoundError('Held-out projection is missing; explicit download is required.')
        download_test(test)
    source_metadata = json.loads(test.with_suffix(test.suffix+'.json').read_text())
    if (source_metadata.get('policy_sha256_before_access') != proof['policy']['file_sha256'] or
        source_metadata.get('protocol_sha256_before_access') != proof['protocol_sha256']):
        raise ValueError('The existing held-out source lacks the matching pre-access freeze receipt.')
    records,metadata = load_records([*history,test])
    if any(r['year'] not in (2023,2024,2025) for r in records.values()):
        raise ValueError('Unexpected occurrence year in the fixed three-year projection.')
    evaluated = evaluate(Corpus(records),proof['policy'],proof['protocol'])
    cohorts = evaluated.pop('cohorts')
    result = {'method_version':'fixed-held-out-2025-v1','year':2025,'held_out_evaluated':True,
        'selection_or_tuning_performed':False,'policy':proof['policy'],'protocol':proof['protocol'],
        'pretest_receipt':receipt,'corpus':metadata,'case_counts':evaluated['case_counts'],
        'question_budget_summaries':evaluated['question_budget_summaries'],'stopping':evaluated['stopping'],
        'notes':['Frozen 2023 fit and user-selected 2024 thresholds; no 2025 refit, vocabulary fit or threshold sweep.',
                 'Abstention-off uses identical selected-policy terminal beliefs/questions, removing only final confidence/evidence gates.',
                 'Correction part is an outcome-key proxy, not fault-cause truth or a sentence-hallucination measure.',
                 'All-attribute answers can reuse initial narrative; coded/structured controls are retained.',
                 'The Mid-I ranker was developed in a project with a prior 2025 POC. This evaluates a newly frozen configuration, not a claim that the project never saw any 2025 report.',
                 'Occurrence-year primary results retain every eligible case; the predeclared label-availability stratum exposes timing overlap.',
                 'Relative support wording remains mandatory; no repair/airworthiness approval.']}
    for pool,cases in cohorts.items():
        path = output/(pool+'_cases.json')
        path.write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    result['case_files_sha256'] = {p.name:sha(p) for p in sorted(output.glob('*_cases.json'))}
    (output/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--data-directory')
    parser.add_argument('--output')
    parser.add_argument('--download',action='store_true')
    args = parser.parse_args()
    if args.preflight_only:
        proof = preflight_procedure()
        print(json.dumps({'preflight':'PASS','policy_sha256':proof['policy']['file_sha256'],
                          'protocol_sha256':proof['protocol_sha256'],'held_out_accessed':False}))
    else:
        if not args.data_directory or not args.output:parser.error('--data-directory and --output are required')
        result = run(args.data_directory,args.output,allow_download=args.download)
        print(json.dumps({'status':'HELD_OUT_EVALUATED','case_counts':result['case_counts']}))
