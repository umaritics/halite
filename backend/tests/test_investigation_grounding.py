"""Grounding maths, citation boundaries and explicit/unconfigured label semantics."""
from types import SimpleNamespace
import math

import pytest

from investigation import embed_port
from investigation.grounding import GroundingParameters, check_reply, content_tokens, split_sentences

RID='AALA2024010100001'
OTHER='SWIA2024020200002'


def params(**kwargs):
    return GroundingParameters(.3,.8,1,provenance='synthetic unit-test fixture; not selected thresholds',**kwargs)


def evidence(text='Pump cracked during climb.',part='PUMP'):
    return [{'record_id':RID,'text':text,'part_name':part}]


def test_sentence_splitter_keeps_decimals_abbreviations_and_trailing_citations():
    text=f'Pressure 3.5 psi, e.g. during climb. [{RID}]\nPump cracked ({RID}). No smoke.'
    assert split_sentences(text)==[f'Pressure 3.5 psi, e.g. during climb. [{RID}]',f'Pump cracked ({RID}).','No smoke.']
    # Consuming a following citation across newline must not move the cursor back.
    assert split_sentences(f'Pump cracked.\n[{RID}]\nNo smoke.')==[f'Pump cracked.\n[{RID}]','No smoke.']
    assert split_sentences('')==[]


def test_tokens_drop_ids_and_hedging_but_preserve_negations_and_numbers():
    assert content_tokens(f'The pump may not have 3.5 psi ({RID}).')=={'pump','not','3.5','psi'}


def test_hand_computed_containment_and_best_single_report():
    result=check_reply(f'Pump cracked during climb {RID}.',evidence(),parameters=params())
    item=result['sentences'][0]
    assert item['score']==1 and item['level']=='supported'
    assert result['checked_with']=='lexical' and result['embedding_status']=='not_requested'
    # Do not join fragments across cited reports into one fabricated explanation.
    rows=[{'record_id':RID,'part_name':'PUMP','text':'Pump cracked.'},{'record_id':OTHER,'part_name':'SENSOR','text':'SENSOR vibration during climb.'}]
    result=check_reply(f'Pump cracked vibration during climb {RID}, {OTHER}.',rows,parameters=params())
    assert result['sentences'][0]['score']==pytest.approx(3/5)
    assert result['sentences'][0]['level']=='weak'


def test_cited_ids_must_be_in_this_saved_evidence_not_elsewhere():
    result=check_reply(f'Pump cracked {RID}, {OTHER}.',evidence(),parameters=params())
    item=result['sentences'][0]
    assert item['level']=='unsupported' and item['invalid_citations']==[OTHER]
    assert item['valid_citations']==[RID] and result['unsupported_count']==1


def test_no_thresholds_never_claim_validated_sentence_support():
    result=check_reply(f'Pump cracked {RID}.',evidence())
    assert result['status']=='thresholds_pending' and result['parameters'] is None
    assert result['sentences'][0]['level']=='unrated'
    assert result['sentences'][0]['score']==1


def test_uncited_is_allowed_only_for_an_exact_explicit_template():
    safety='This ranking is provisional.'
    result=check_reply(safety+' Pump cracked.',evidence(),parameters=params(whitelist=(safety,)))
    assert [s['level'] for s in result['sentences']]==['uncited','uncited']
    assert [s['acceptable_uncited'] for s in result['sentences']]==[True,False]
    assert result['uncited_count']==1
    assert check_reply('This ranking is provisional. Pump repaired.',[],parameters=params(whitelist=(safety,)))['sentences'][1]['acceptable_uncited'] is False


def test_dense_cosine_is_weighted_and_lexical_guards_cannot_be_overridden():
    p=GroundingParameters(.2,.6,.5,provenance='synthetic test')
    # Token overlap 2/3, cosine=1, weighted score=5/6; missing condition blocks supported.
    result=check_reply(f'Pump cracked vibration {RID}.',evidence('Pump cracked.'),parameters=p,embedder=lambda texts:[[1,0]]*len(texts))
    item=result['sentences'][0]
    assert item['score']==pytest.approx(5/6)
    assert item['level']=='weak' and item['candidates'][0]['guards']['missing_conditions']==['vibration']
    assert result['checked_with']=='lexical+dense'


def test_named_part_quantity_and_negation_guards_are_exposed():
    rows=evidence('Pump cracked at 3 psi.')+[{'record_id':OTHER,'part_name':'SENSOR','text':'Sensor test.'}]
    p=GroundingParameters(.1,.3,.2,provenance='synthetic guard test')
    result=check_reply(f'SENSOR not cracked at 8 psi {RID}.',rows,parameters=p,embedder=lambda texts:[[1]]*len(texts))
    item=result['sentences'][0]
    assert item['level']=='weak'
    guards=item['candidates'][0]['guards']
    assert guards['missing_parts']==['sensor'] and guards['missing_numbers']==['8'] and guards['negation_mismatch']


def test_optional_embedding_failure_is_explicit_lexical_fallback():
    def failed(texts):
        raise RuntimeError('synthetic encoder failure')
    p=GroundingParameters(.3,.8,.5,provenance='synthetic test')
    result=check_reply(f'Pump cracked {RID}.',evidence(),parameters=p,embedder=failed)
    assert result['checked_with']=='lexical' and result['embedding_status']=='failed:RuntimeError'
    assert result['sentences'][0]['score']==1
    for vectors in ([[1]],[[float('nan')],[1]],[[1,2],[1]], [[],[]]):
        result=check_reply(f'Pump cracked {RID}.',evidence(),parameters=p,embedder=lambda texts:vectors)
        assert result['checked_with']=='lexical' and result['embedding_status'].startswith('failed:')


@pytest.mark.parametrize('lo,hi,w',[(.8,.3,1),(-.1,.8,1),(.3,1.1,1),(.3,.8,2),(.3,.8,float('nan')),(True,.8,1)])
def test_invalid_parameters_fail(lo,hi,w):
    with pytest.raises(ValueError):
        GroundingParameters(lo,hi,w,provenance='synthetic test')


def test_empty_evidence_citation_only_and_zero_dense_vectors_cannot_be_supported():
    assert check_reply(f'Pump {RID}.',[],parameters=params())['sentences'][0]['level']=='unsupported'
    p=GroundingParameters(.1,.2,0,provenance='synthetic test')
    assert check_reply(f'{RID}.',evidence(),parameters=p,embedder=lambda texts:[[1]]*len(texts))['sentences'][0]['level']=='weak'
    assert check_reply(f'Pump {RID}.',evidence(),parameters=p,embedder=lambda texts:[[0]]*len(texts))['sentences'][0]['level']=='unsupported'


def test_embed_port_absence_and_installed_failure_are_distinct(monkeypatch):
    def missing(name):
        raise ModuleNotFoundError(name='retrieval')
    monkeypatch.setattr(embed_port,'import_module',missing)
    assert embed_port.embed_texts(['pump']) is None
    def broken(name):
        raise ModuleNotFoundError(name='unexpected_encoder_dependency')
    monkeypatch.setattr(embed_port,'import_module',broken)
    with pytest.raises(ModuleNotFoundError):
        embed_port.embed_texts(['pump'])
    monkeypatch.setattr(embed_port,'import_module',lambda name:SimpleNamespace(embed_texts=lambda texts:[[1,0]]))
    assert embed_port.embed_texts(['pump'])==[[1,0]]
    with pytest.raises(ValueError):
        embed_port.embed_texts(['pump','sensor'])
    monkeypatch.setattr(embed_port,'import_module',lambda name:SimpleNamespace(embed_texts=lambda texts:[[math.nan]]))
    with pytest.raises(ValueError):
        embed_port.embed_texts(['pump'])


@pytest.mark.parametrize('rid',['QR9R2024082100001','N6WA2024110402','2024FA0000588','3J7R2024083000001'])
def test_real_mixed_and_numeric_leading_faa_ids_remain_attached_and_checked(rid):
    claim=f'Pump cracked. [{rid}]'
    assert split_sentences(claim)==[claim]
    result=check_reply(claim,[{'record_id':rid,'text':'Pump cracked.','part_name':'PUMP'}])
    assert result['sentences'][0]['valid_citations']==[rid]
    assert result['sentences'][0]['score']==1
    invented=check_reply(claim,[])['sentences'][0]
    assert invented['invalid_citations']==[rid] and invented['level']=='unsupported'
