import copy

import pytest

from investigation.attributes import load_codebook
from investigation.experiments.simulated_technician import POLICIES, score_trace, simulate, summarize


def models():
    return {'stage_of_operation': {'values':['CL','CR'],'matrix':[[1,0],[0,1],[.5,.5]]},
            'how_discovered': {'values':['V','C'],'matrix':[[.5,.5]]*3}}


def test_answer_path_uses_only_original_attributes_and_evaluation_is_separate():
    original={'stage_of_operation':'CR','how_discovered':'V'}
    trace=simulate([.4,.4,.2],models(),original,codebook=load_codebook(),strategy='information_gain',query_id='QUERY001')
    assert trace[1]['attribute']=='stage_of_operation' and trace[1]['answer']=='CR'
    assert trace[1]['beliefs']==pytest.approx([0,.8,.2])
    assert original=={'stage_of_operation':'CR','how_discovered':'V'}
    saved=copy.deepcopy(trace)
    # Changing the correcting report's answer key changes evaluation only.
    first=score_trace(trace,['A','B'],'A')
    second=score_trace(trace,['A','B'],'B')
    assert first[1]['top1']==0 and second[1]['top1']==1
    assert trace==saved
    assert second[0]['top1']==0  # stable initial-rank tie chooses A before any question.


def test_not_sure_preserves_beliefs_removes_attribute_and_budget_is_bounded():
    trace=simulate([.4,.4,.2],models(),{},codebook=load_codebook(),strategy='information_gain',query_id='Q')
    assert trace[1]['answer']=='not_sure' and trace[1]['beliefs']==trace[0]['beliefs']
    assert [s['attribute'] for s in trace[1:]]==['stage_of_operation','how_discovered',None]
    assert trace[-1]['questions_asked']==2
    assert len(trace)==4


def test_random_is_seeded_per_original_and_no_questions_repeats_state():
    kwargs=dict(codebook=load_codebook(),query_id='ORIGINAL001',seed=5)
    a=simulate([.4,.4,.2],models(),{'stage_of_operation':'CL'},strategy='random',**kwargs)
    b=simulate([.4,.4,.2],models(),{'stage_of_operation':'CL'},strategy='random',**kwargs)
    assert a==b
    no=simulate([.4,.4,.2],models(),{},strategy='no_questions',**kwargs)
    assert all(step['beliefs']==[.4,.4,.2] and step['questions_asked']==0 for step in no)


def test_summary_clusters_shared_originals_and_paired_differences():
    prior=[.4,.4,.2]
    traces={p:simulate(prior,models(),{'stage_of_operation':'CR','how_discovered':'V'},codebook=load_codebook(),strategy=p,query_id='ORIGINAL001',seed=5) for p in POLICIES}
    cases=[{'query_id':'ORIGINAL001','metrics':{p:score_trace(t,['A','B'],target) for p,t in traces.items()}} for target in ['A','B']]
    result=summarize(cases,resamples=10)
    assert result['n_pairs']==2 and result['n_originals']==1
    assert result['policies']['information_gain'][1]['top1']==.5
    assert result['policies']['information_gain'][1]['ci95']['top1']['low']==.5
    for policy in POLICIES:
        assert result['policies'][policy][0]['top1']==.5
        assert len(result['policies'][policy])==4
    assert result==summarize(cases,resamples=10)


def test_full_pipeline_fixture_answers_original_and_exports_real_sample_counts(tmp_path):
    import csv
    import json
    import math
    from investigation.beliefs import BeliefParameters
    from investigation.experiments.download_projection import COLUMNS
    from investigation.experiments.offline import load_records
    from investigation.experiments.simulated_technician import run

    def raw(rid,year,part,stage,text):
        r=dict.fromkeys(COLUMNS,'')
        r.update(OperatorControlNumber=rid,DifficultyDate=f'01/01/{year}',SubmissionDate=f'{year}-01-02T00:00:00Z',
                 RegistryNNumber='N1',AircraftMake='M',AircraftModel='ONE',PartName=part,StageOfOperationCode=stage,
                 HowDiscoveredCode='V',NatureOfConditionA='K',PrecautionaryProcedureA='K',Discrepancy=text)
        return r
    fit=tmp_path/'fit.csv'
    select=tmp_path/'select.csv'
    def write(path,rows):
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=COLUMNS)
            writer.writeheader();writer.writerows(rows)
    write(fit,[raw('PAST0001',2023,'A','CL','pressure loss'),raw('PAST0002',2023,'B','CR','pressure loss')])
    q=raw('QUERY001',2024,'UNKNOWN','CR','initial pressure loss')
    correction=raw('CORRECT1',2024,'B','CL','SUPPLEMENTAL REPORT FOR (QUERY001): finding')
    correction['SubmissionDate']='2024-01-03T00:00:00Z'
    write(select,[q,correction])
    _,fit_meta=load_records([fit])
    _,meta=load_records([fit,select])
    baseline=tmp_path/'investigation/experiments/results/baseline'
    baseline.mkdir(parents=True)
    params=BeliefParameters('mid_heuristic-v1',1,0,(2023,),fit_meta['corpus_sha256']).as_dict()
    params_dir=tmp_path/'investigation/params'
    params_dir.mkdir()
    (params_dir/'mid_heuristic-v1.json').write_text(json.dumps(params))
    (baseline/'selection.json').write_text(json.dumps({'held_out_evaluated':False,'ranker_version':'mid_heuristic-v1',
        'fit_corpus':fit_meta,'selection_corpus':meta,'fit':{'parameters':params}}))
    (baseline/'selection_cases.json').write_text(json.dumps([{'case_id':'QUERY001->CORRECT1','query_id':'QUERY001','year':2024,
        'ranker_version':'mid_heuristic-v1','answer_part':'B','part_change':'unknown_to_named',
        'hypotheses':[{'part_name':'A','score':math.log(2),'evidence_count':2},{'part_name':'B','score':math.log(2),'evidence_count':2}]}]))
    output=tmp_path/'result'
    result=run(sources=[fit,select],baseline_directory=baseline,output=output,resamples=5)
    assert result['summaries']['coded_fields_only']['all']['n_pairs']==1
    assert result['held_out_evaluated'] is False
    cases=json.loads((output/'coded_fields_only_cases.json').read_text())
    first=cases[0]['traces']['information_gain'][1]
    assert first['attribute']=='stage_of_operation' and first['answer']=='CR'
    assert cases[0]['audit']['n_visible_records']==2
    assert '1 correction pairs, 1 original reports' in (output/'QUESTION_TABLE.md').read_text()
    assert result['summaries']['coded_fields_only']['all']['policies']['information_gain'][1]['top1']==1
    with pytest.raises(FileExistsError):
        run(sources=[fit,select],baseline_directory=baseline,output=output,resamples=5)
