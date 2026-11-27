"""Synthetic 2025 fixtures only; never access the real held-out source in tests."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest

from investigation.experiments import held_out as module
from investigation.experiments.download_projection import COLUMNS
from investigation.experiments.frozen_policy import preflight_held_out
from investigation.experiments.offline import Corpus, load_records


def raw(rid,year,*,day='01',part='PUMP',text='Synthetic pump pressure difficulty.',code='CL'):
    row = dict.fromkeys(COLUMNS,'')
    row.update(OperatorControlNumber=rid,DifficultyDate=f'01/{day}/{year}',
               SubmissionDate=f'{year}-01-{day}T12:00:00-05:00',RegistryNNumber='N-SYNTHETIC',
               AircraftMake='SYNTHETIC',AircraftModel='FIXTURE',PartName=part,
               PartCondition='CRACKED' if part=='PUMP' else 'WORN',
               StageOfOperationCode=code,Discrepancy=text,JASCCode='2900')
    return row


def write_projection(path,rows,*,test_metadata=None):
    digest = hashlib.sha256()
    with gzip.open(path,'wt',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=COLUMNS);writer.writeheader()
        for row in rows:
            writer.writerow(row)
            digest.update((json.dumps({k:row[k] for k in COLUMNS},ensure_ascii=False,separators=(',',':'))+'\n').encode())
    path.with_suffix(path.suffix+'.json').write_text(json.dumps({'projection_sha256':digest.hexdigest(),**(test_metadata or {})}))


@pytest.fixture()
def synthetic_sources(tmp_path):
    history = [raw('SYNHIST2023001',2023),raw('SYNHIST2023002',2023,day='02'),
               raw('SYNHIST2023003',2023,day='03',part='SENSOR',code='CR'),
               raw('SYNHIST2023004',2023,day='04',part='SENSOR',code='CR')]
    test = [raw('SYNQUERY2025001',2025,part='UNKNOWN'),
            raw('SYNANSWER2025001',2025,day='06',text='SUPPLEMENTAL REPORT FOR SYNQUERY2025001. Synthetic pump finding.'),
            raw('SYNQUERY2025002',2025,day='03',part='UNKNOWN'),
            raw('SYNANSWER2025002',2025,day='07',part='SENSOR',text='SUPPLEMENTAL REPORT FOR SYNQUERY2025002. Synthetic sensor finding.')]
    proof=preflight_held_out()
    paths=[]
    for year,rows in ((2023,history),(2024,[]),(2025,test)):
        path=tmp_path/f'usman_decision_{year}.csv.gz'
        write_projection(path,rows,test_metadata={'policy_sha256_before_access':proof['policy']['file_sha256'],
                                                'protocol_sha256_before_access':proof['protocol_sha256']})
        paths.append(path)
    return paths


def test_terminal_ece_is_hand_computed_and_empty_rankings_have_zero_confidence():
    rows=[{'query_id':'A','confidence':.9,'correct_top1':True},
          {'query_id':'B','confidence':.1,'correct_top1':False}]
    result=module.calibration(rows,np.array([[1,1],[2,0],[0,2]]))
    assert result['value']==pytest.approx(.1)
    assert result['ci95']['low']==pytest.approx(.1) and result['ci95']['high']==pytest.approx(.1)
    assert sum(b['n'] for b in result['bins'])==2
    assert module.terminal_calibration({'query_id':'A','answer_part':'PUMP'},
        {'named_order':[],'beliefs':[1]})=={'query_id':'A','confidence':0,'correct_top1':False}
    with pytest.raises(ValueError,match='nonempty'):
        module.calibration([],np.zeros((1,0)))
    with pytest.raises(ValueError,match='bounded'):
        module.calibration([{'query_id':'A','confidence':float('nan'),'correct_top1':False}],np.ones((1,1)))


def test_actual_ranker_simulation_and_fixed_stopping_keep_temporal_and_outcome_boundaries(synthetic_sources):
    records,_=load_records(synthetic_sources)
    proof=preflight_held_out()
    result=module.evaluate(Corpus(records),proof['policy'],proof['protocol'])
    assert result['case_counts']['n_pairs']==2 and result['case_counts']['n_originals']==2
    assert result['case_counts']['before_or_at_selection_label_time_pairs']==1
    assert len(result['stopping'])>0
    for table in result['stopping']:
        assert table['chosen']['mean_questions']==table['abstention_off']['mean_questions']
        assert table['chosen']['n_answered']<=table['abstention_off']['n_answered']
    for pool,cases in result['cohorts'].items():
        for case in cases:
            assert case['audit']['strict_submission_bound'] and case['audit']['query_chain_excluded']
            assert len(case['traces']['information_gain'])==4
            assert case['metrics']['no_questions'][0]==case['metrics']['no_questions'][3]
    # Change the future correction key. Its own chain is excluded from all
    # query features; questions and beliefs must stay identical, scoring changes.
    records['SYNANSWER2025001']['part_name']='DOOR'
    changed=module.evaluate(Corpus(records),proof['policy'],proof['protocol'])
    for pool,cases in result['cohorts'].items():
        original=next(c for c in cases if c['query_id']=='SYNQUERY2025001')
        revised=next(c for c in changed['cohorts'][pool] if c['query_id']=='SYNQUERY2025001')
        assert original['traces']==revised['traces'] and original['stopped']==revised['stopped']
        assert original['answer_part']!=revised['answer_part']


def test_download_requires_preflight_before_any_request_and_cleans_partial_failures(tmp_path,monkeypatch):
    def denied():raise ValueError('synthetic preflight refusal')
    def network_forbidden(*args,**kwargs):pytest.fail('No network is permitted in these tests')
    monkeypatch.setattr(module,'preflight_procedure',denied)
    monkeypatch.setattr(module.urllib.request,'urlopen',network_forbidden)
    with pytest.raises(ValueError,match='preflight refusal'):module.download_test(tmp_path/'test.gz')
    monkeypatch.setattr(module,'preflight_procedure',preflight_held_out)
    for content in (b'wrong,headers\n1,2\n',(','.join(COLUMNS)+'\n').encode()):
        monkeypatch.setattr(module.urllib.request,'urlopen',lambda *args,**kwargs:io.BytesIO(content))
        with pytest.raises(ValueError):module.download_test(tmp_path/'test.gz')
        assert not (tmp_path/'test.gz').exists() and not (tmp_path/'test.gz.partial').exists()


def test_download_canonical_projection_and_pre_access_fingerprints_are_saved(tmp_path,monkeypatch):
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=COLUMNS);writer.writeheader()
    row=raw('SYNTHETIC2025001',2025,text='Synthetic comma, quote " and Unicode α.')
    writer.writerow(row)
    monkeypatch.setattr(module,'preflight_procedure',preflight_held_out)
    monkeypatch.setattr(module.urllib.request,'urlopen',lambda *args,**kwargs:io.BytesIO(buffer.getvalue().encode()))
    path=tmp_path/'source.csv.gz';meta=module.download_test(path)
    records,loaded=load_records([path])
    assert len(records)==1 and meta['n_rows']==1
    assert loaded['sources'][0]['projection_sha256']==meta['projection_sha256']
    assert meta['policy_sha256_before_access']==preflight_held_out()['policy']['file_sha256']
    with pytest.raises(FileExistsError):module.download_test(path)


def test_full_synthetic_export_and_independent_verification(synthetic_sources,tmp_path,monkeypatch):
    # Use a tiny, explicitly synthetic history baseline; keep the actual frozen
    # belief/schema files and policy. This is not a measured FAA test result.
    root=tmp_path/'fixture-investigation'
    for name in ('mid_heuristic-v1.json','report-attributes-v1.json'):
        destination=root/'params'/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(module.ROOT/'params'/name,destination)
    _,history=load_records(synthetic_sources[:2])
    baseline=root/'experiments/results/decision_selection_2024_v2/selection.json'
    baseline.parent.mkdir(parents=True,exist_ok=True);baseline.write_text(json.dumps({'selection_corpus':history}))
    monkeypatch.setattr(module,'ROOT',root)
    monkeypatch.setattr(module,'preflight_procedure',preflight_held_out)
    monkeypatch.setattr(module.urllib.request,'urlopen',lambda *a,**k:pytest.fail('Synthetic export never uses network'))
    output=tmp_path/'synthetic-results'
    result=module.run(tmp_path,output)
    assert result['case_counts']['n_pairs']==2 and result['selection_or_tuning_performed'] is False
    assert len(result['case_files_sha256'])==3 and (output/'pretest-receipt.json').exists()
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'docs/work/usman'))
    from verify_held_out import verify
    assert verify(output)['independent_held_out_point_metrics']=='PASS'
    with pytest.raises(FileExistsError):module.run(tmp_path,output)
    # An appended history row is removed only through an exact original hash.
    with gzip.open(synthetic_sources[0],'rt',newline='') as stream:old_rows=list(csv.DictReader(stream))
    spec=json.loads(synthetic_sources[0].with_suffix(synthetic_sources[0].suffix+'.json').read_text())
    index=tmp_path/'synthetic-order.json.gz'
    with gzip.open(index,'wt') as stream:json.dump({'years':{'2023':{'ordered_ids':[r['OperatorControlNumber'] for r in old_rows],'projection_sha256':spec['projection_sha256']}}},stream)
    write_projection(synthetic_sources[0],[*old_rows,raw('SYNEXTRA2023001',2023,day='08')])
    monkeypatch.setattr(module,'HISTORY_INDEX',str(index))
    restored=module.run(tmp_path,tmp_path/'synthetic-restored-results')
    assert restored['case_counts']==result['case_counts']
    assert restored['pretest_receipt']['history_restorations'][0]['original_full_hash_verified']
    baseline.write_text(json.dumps({'selection_corpus':{'corpus_sha256':'different-history'}}))
    with pytest.raises(ValueError,match='Historical FAA projections changed'):
        module.run(tmp_path,tmp_path/'refused-results')
    assert not (tmp_path/'refused-results').exists()


def test_procedure_requires_frozen_implementation_and_verifier(monkeypatch):
    proof=preflight_held_out();proof['protocol']['procedure_files_sha256']={}
    monkeypatch.setattr(module,'preflight_held_out',lambda:proof)
    with pytest.raises(ValueError,match='complete evaluation procedure'):module.preflight_procedure()


def test_history_restoration_ignores_additions_restores_order_and_keeps_full_original_hash(tmp_path):
    old=[raw('SYNOLD2024001',2024),raw('SYNOLD2024002',2024,day='02')]
    path=tmp_path/'history.csv.gz';write_projection(path,old)
    expected=json.loads(path.with_suffix(path.suffix+'.json').read_text())['projection_sha256']
    write_projection(path,[raw('SYNEXTRA2024001',2024),old[1],old[0]])
    restored=module.restore_history(path,{'ordered_ids':[r['OperatorControlNumber'] for r in old],
                                        'projection_sha256':expected})
    assert restored['original_full_hash_verified'] is True
    assert restored['excluded_new_ids']==['SYNEXTRA2024001']
    assert restored['restored_projection_sha256']==expected
    with gzip.open(path,'rt',newline='') as stream:assert list(csv.DictReader(stream))==old
    assert path.with_name(path.name+'.retrieved').exists()
    assert path.with_suffix(path.suffix+'.json').with_name(path.name+'.json.retrieved').exists()


@pytest.mark.parametrize('change', ['modified','missing'])
def test_history_restoration_rejects_changed_or_missing_frozen_content(tmp_path,change):
    original=raw('SYNOLD2024001',2024)
    path=tmp_path/'history.csv.gz';write_projection(path,[original])
    expected=json.loads(path.with_suffix(path.suffix+'.json').read_text())['projection_sha256']
    changed={**original,'Discrepancy':'Materially changed synthetic narrative.'}
    write_projection(path,[changed] if change=='modified' else [raw('SYNEXTRA2024001',2024)])
    before=path.read_bytes()
    with pytest.raises(ValueError):
        module.restore_history(path,{'ordered_ids':['SYNOLD2024001'],'projection_sha256':expected})
    assert path.read_bytes()==before and not path.with_suffix(path.suffix+'.restore.partial').exists()
