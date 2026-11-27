"""Independent fixed-policy scoring and replay of all held-out interval artifacts."""
import hashlib
import json
import math
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'backend'))
from investigation.experiments.frozen_policy import preflight_held_out
from investigation.experiments.simulated_technician import summarize
from verify_policy_selection import independent


def close(actual, expected):
    if isinstance(expected,dict):
        assert actual.keys()==expected.keys()
        for key in expected:close(actual[key],expected[key])
    elif isinstance(expected,list):
        assert len(actual)==len(expected)
        for a,b in zip(actual,expected):close(a,b)
    elif isinstance(expected,float):
        assert math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-12),(actual,expected)
    else:assert actual==expected,(actual,expected)


def verify(directory):
    from investigation.experiments.policy_selection import cluster_weights, summarize as stopping_summary
    from investigation.experiments.held_out import calibration
    directory = Path(directory)
    result = json.loads((directory/'results.json').read_text())
    frozen = preflight_held_out()
    assert result['held_out_evaluated'] is True and result['selection_or_tuning_performed'] is False
    assert result['policy']==frozen['policy'] and result['protocol']==frozen['protocol']
    protocol = result['protocol']
    params = result['policy']['parameters']
    cohorts = {}
    for name,expected in result['case_files_sha256'].items():
        path = directory/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        cohorts[name.removesuffix('_cases.json')] = json.loads(path.read_text())
    for pool,cases in cohorts.items():
        assert len(cases)==result['case_counts']['n_pairs']
        for case in cases:
            assert case['year']==2025 and case['audit']['query_chain_excluded'] and case['audit']['strict_submission_bound']
            for strategy,trace in case['traces'].items():
                measured = []
                for step in trace:
                    values = step['beliefs'];names = case['names']
                    assert math.isclose(sum(values),1,abs_tol=1e-9)
                    order = sorted(range(len(names)),key=lambda i:(-values[i],i))
                    ranked = [names[i] for i in order]
                    entropy = -sum(p*math.log2(p) for p in values if p)
                    assert math.isclose(entropy,step['entropy'],abs_tol=1e-10)
                    measured.append({'top1':float(bool(ranked) and ranked[0]==case['answer_part']),
                                     'top3':float(case['answer_part'] in ranked[:3]),'entropy':step['entropy'],
                                     'questions_asked':step['questions_asked']})
                close(case['metrics'][strategy],measured)
        for key,expected in result['question_budget_summaries'][pool].items():
            availability,stratum = key.split('/')
            rows = cases if availability=='primary_all' else [c for c in cases if c['after_selection_labels']]
            rows = rows if stratum=='all' else [c for c in rows if c['part_change']==stratum]
            if rows:close(expected,summarize(rows,seed=protocol['seed'],resamples=protocol['bootstrap_resamples']))
            else:assert expected=={'status':'empty','n_pairs':0,'n_originals':0}
    checked = 0
    for table in result['stopping']:
        cases = cohorts[table['cohort']]
        if table['availability']!='primary_all':cases=[c for c in cases if c['after_selection_labels']]
        if table['stratum']!='all':cases=[c for c in cases if c['part_change']==table['stratum']]
        point = {'strategy':table['strategy'],'tau_answer':params['tau_answer'],'g_min':params['g_min']}
        baseline = {c['case_id']:c for c in cases}
        direct = independent(cases,baseline,point,{**protocol,'n_min':params['n_min'],'max_questions':params['max_questions']})
        for key,value in direct.items():close(table['chosen'][key],value)
        chosen_stats,off_stats,eces = [],[],[]
        for case in cases:
            state = case['stopped'][table['strategy']]
            named = state['named_order'];answer=state['decision']=='answer';top1=bool(named) and named[0]==case['answer_part'];top3=case['answer_part'] in named[:3]
            chosen_stats.append([1,int(answer),int(answer and top1),int(answer and top3),state['questions_asked'],int(not answer)])
            off_stats.append([1,int(bool(named)),int(top1),int(top3),state['questions_asked'],int(not named)])
            eces.append({'query_id':case['query_id'],'confidence':max(state['beliefs'][:-1],default=0),'correct_top1':top1})
        queries=[c['query_id'] for c in cases]
        weights=cluster_weights(sorted(set(queries)),seed=protocol['seed'],resamples=protocol['bootstrap_resamples'])
        close(table['chosen'],stopping_summary(chosen_stats,queries,weights=weights))
        close(table['abstention_off'],stopping_summary(off_stats,queries,weights=weights))
        close(table['named_top_ece'],calibration(eces,weights))
        assert table['chosen']['mean_questions']==table['abstention_off']['mean_questions']
        checked += 1
    summary={'independent_held_out_point_metrics':'PASS','all_question_and_stopping_intervals_replayed':'PASS',
             'tables_verified':checked,'case_counts':result['case_counts'],
             'policy_sha256':result['policy']['file_sha256'],'held_out_tuning':False,
             'results_sha256':hashlib.sha256((directory/'results.json').read_bytes()).hexdigest()}
    (directory/'verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':verify(sys.argv[1])
