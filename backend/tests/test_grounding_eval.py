"""Synthetic math/protocol checks; never stand in for the required human labels."""
import csv
import json

import pytest

from investigation.experiments.grounding_eval import agreement, consensus, evaluate_files, load_labels, metrics, select_thresholds
from investigation.experiments.grounding_packet import review_fingerprint, review_html


def rows(labels,name):
    return {str(i):{'pair_id':str(i),'label':label,'reviewer':name,'reviewed_at':'2026-11-20T00:00:00Z','rationale':'Synthetic test rationale'} for i,label in enumerate(labels)}


def test_cohens_kappa_is_hand_computed_and_constant_marginals_stay_undefined():
    a=rows(['supported','supported','unsupported','unsupported','partly_supported','partly_supported'],'synthetic_A')
    b=rows(['supported','unsupported','unsupported','unsupported','partly_supported','supported'],'synthetic_B')
    result=agreement(a,b)
    assert result['observed_agreement']==pytest.approx(2/3)
    assert result['expected_agreement']==pytest.approx(1/3)
    assert result['cohens_kappa']==pytest.approx(.5)
    assert result['disagreement_ids']==['1','5']
    assert agreement(rows(['supported'],'A'),rows(['supported'],'B'))['cohens_kappa'] is None
    with pytest.raises(ValueError,match='distinct'):
        agreement(rows(['supported'],'Same Reviewer'),rows(['supported'],' same  reviewer '))


def test_disagreements_require_explicit_adjudication_and_no_extra_ids():
    a=rows(['supported','unsupported'],'synthetic_A');b=rows(['unsupported','unsupported'],'synthetic_B')
    with pytest.raises(ValueError,match='adjudication'):
        consensus(a,b)
    result,_=consensus(a,b,{'0':{'label':'partly_supported','reviewer':'synthetic adjudicator','rationale':'Synthetic partial test'}})
    assert result=={'0':'partly_supported','1':'unsupported'}
    with pytest.raises(ValueError,match='exactly'):
        consensus(a,b,{'0':{},'extra':{}})


def test_precision_recall_and_f1_are_hand_computed():
    result=metrics({'1':'supported','2':'unsupported','3':'weak','4':'unsupported'},
                   {'1':'supported','2':'supported','3':'partly_supported','4':'unsupported'})
    assert result['accuracy']==.75
    assert result['classes']['supported']['precision']==1
    assert result['classes']['supported']['recall']==.5
    assert result['classes']['unsupported']['precision']==.5
    assert result['classes']['unsupported']['recall']==1
    assert result['classes']['supported']['f1']==pytest.approx(2/3)
    assert metrics({'1':'weak'},{'1':'supported'})['classes']['supported']['precision'] is None


def write_labels(path,labels,*,fingerprint='synthetic-packet'):
    with path.open('w',newline='') as stream:
        keys=['pair_id','label','reviewer','reviewed_at','rationale','packet_sha256']
        writer=csv.DictWriter(stream,fieldnames=keys);writer.writeheader()
        writer.writerows({**r,'packet_sha256':fingerprint} for r in labels.values())


def test_label_import_rejects_missing_empty_foreign_duplicate_and_wrong_packet(tmp_path):
    path=tmp_path/'labels.csv'
    valid=rows(['supported','unsupported'],'synthetic_A')
    write_labels(path,valid)
    assert len(load_labels(path,expected_ids=set(valid),packet_sha256='synthetic-packet'))==2
    with pytest.raises(ValueError,match='different'):
        load_labels(path,expected_ids=set(valid),packet_sha256='other')
    for field,value in [('label',''),('reviewer',''),('rationale',''),('reviewed_at','2026-11-20')]:
        broken=rows(['supported','unsupported'],'synthetic_A');broken['0'][field]=value
        write_labels(path,broken)
        with pytest.raises(ValueError):load_labels(path,expected_ids=set(valid))
    write_labels(path,{'0':valid['0']})
    with pytest.raises(ValueError,match='Incomplete'):load_labels(path,expected_ids=set(valid))
    write_labels(path,valid)
    with path.open('a') as stream:stream.write('0,supported,A,2026-11-20T00:00:00Z,test,synthetic-packet\n')
    with pytest.raises(ValueError,match='duplicate'):load_labels(path,expected_ids=set(valid))


def packet_pairs():
    result=[]
    for index in range(6):
        rid=f'AALA20240101{index:05}'
        result.append({'pair_id':str(index),'original_id':'fit' if index<3 else 'validation','year':2024,
                       'sentence':f"{'Pump cracked with vibration' if index%3==1 else 'Pump cracked'} {rid}.",'report':{'record_id':rid,'part_name':'PUMP',
                       'text':['Pump cracked.','Pump cracked.','Sensor vibration.'][index%3]}})
    return result


def test_full_threshold_proposal_keeps_validation_separate_and_replays_from_files(tmp_path):
    pairs=packet_pairs();labels=['supported','partly_supported','unsupported']*2
    p=tmp_path/'packet.json';fp=review_fingerprint(pairs)
    p.write_text(json.dumps({'pairs':pairs,'fit_originals':['fit'],'validation_originals':['validation'],'review_sha256':fp}))
    a=tmp_path/'a.csv';b=tmp_path/'b.csv';out=tmp_path/'proposal.json'
    write_labels(a,rows(labels,'synthetic_A'),fingerprint=fp);write_labels(b,rows(labels,'synthetic_B'),fingerprint=fp)
    result=evaluate_files(p,a,b,output=out)
    assert result['fit_n']==3 and result['validation_n']==3
    assert result['accepted'] is False and result['held_out_2025_used'] is False
    assert result['agreement']['cohens_kappa']==1
    assert result==json.loads(out.read_text())
    with pytest.raises(FileExistsError):evaluate_files(p,a,b,output=out)
    with pytest.raises(ValueError,match='disjoint'):
        select_thresholds(pairs,dict(enumerate(labels)),fit_originals=['fit'],validation_originals=['fit'])
    pairs[-1]['year']=2025
    with pytest.raises(ValueError,match='2023/2024'):
        select_thresholds(pairs,{str(i):l for i,l in enumerate(labels)},fit_originals=['fit'],validation_originals=['validation'])


def test_review_view_is_blind_to_sampling_arm_and_escapes_script_injection():
    pairs=packet_pairs();pairs[0].update(sampling_arm='HIDDEN_SAMPLING_ARM',checker_score=.99)
    pairs[0]['report']['text']='</script><script>alert("not executable")</script>'
    page=review_html(pairs)
    assert 'HIDDEN_SAMPLING_ARM' not in page and 'checker_score' not in page
    assert '</script><script>alert' not in page
    assert 'Nothing is sent to a server' in page and 'Export completed CSV' in page


def test_pair_builder_preserves_source_groups_and_has_no_reference_leakage():
    from investigation.experiments.grounding_packet import make_pairs
    from investigation.experiments.offline import Corpus,timestamp
    records={}
    queries=[]
    for i in range(2):
        for suffix,date,part,text in [
            ('QUERY','2024-03-01',f'PUMP{i}','The hydraulic pump showed pressure loss during initial climb.'),
            ('PAST','2023-01-01',f'PUMP{i}','The earlier pump lost hydraulic pressure during cruise.'),
            ('OTHER','2023-02-01',f'SENSOR{i}','The sensor gave a pressure warning during climb.')]:
            rid=f'{suffix}{i}'
            records[rid]={'record_id':rid,'part_name':part,'jasc_code':str(i),'text':text,'asset_key':f'N{i}',
                          'year':int(date[:4]),'occurred_at':date,'submitted_at':timestamp(date+'T00:00:00Z')}
            if suffix=='QUERY':queries.append(rid)
    pairs,fit,validation=make_pairs(Corpus(records),queries,groups=2)
    assert len(pairs)==6 and not set(fit)&set(validation)
    fit_refs={p['report']['record_id'] for p in pairs if p['original_id'] in fit}
    val_refs={p['report']['record_id'] for p in pairs if p['original_id'] in validation}
    assert not fit_refs&val_refs
    assert len({p['pair_id'] for p in pairs})==6
    assert len([p for p in pairs if p['sampling_arm']=='same_source'])==2
    with pytest.raises(ValueError,match='Insufficient'):
        make_pairs(Corpus(records),queries,groups=50)
