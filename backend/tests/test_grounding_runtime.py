"""Sentence auditing in actual session/diagnose paths without altering legacy prose."""
import json

import pytest

from investigation.grounding_runtime import annotate
from tests.test_investigation_sessions import environment, create
from tests.test_api_diagnostics import _LiveGroq, _seed_faa_asset


def settings_file(tmp_path,*,weight=1):
    path=tmp_path/'synthetic-grounding.json'
    path.write_text(json.dumps({'status':'experimental','parameters':{'theta_lo':.3,'theta_hi':.8,'lexical_weight':weight,
                 'whitelist':['This ranking is provisional.'],'provenance':'Synthetic unit/integration fixture, not selected thresholds or human labels'}}))
    return str(path)


def test_diagnose_adds_sentence_sources_without_altering_explanation_or_evidence_contract(client):
    asset=_seed_faa_asset(client.app)
    text='Hydraulic pump leak at seal SWIA2025091876593. Invented vibration ZZZZ2024123456789.'
    client.app.state.groq_service=_LiveGroq(text)
    response=client.post('/api/maintenance/diagnose',json={'asset_id':asset,'symptom_text':'hydraulic leak'})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['explanation']=='Hydraulic pump leak at seal SWIA2025091876593. Invented vibration [UNVERIFIED:ZZZZ2024123456789].'
    audit=result['grounding']
    assert audit['status']=='thresholds_pending' and audit['checked_with']=='lexical'
    assert audit['sentences'][0]['level']=='unrated' and audit['sentences'][0]['score']==1
    assert audit['sentences'][1]['level']=='unsupported'
    assert audit['sentences'][1]['invalid_citations']==['ZZZZ2024123456789']
    assert any(r['text']=='Hydraulic pump leak at seal' for r in audit['evidence'])
    assert all('text' not in r for r in result['evidence'])  # frozen metadata-only evidence unchanged
    assert [span['token'] for span in audit['sentences'][0]['candidates'][0]['source_matches']['spans']] == ['hydraulic', 'pump', 'leak', 'seal']


def test_grounding_setting_change_rechecks_cached_prose_without_new_model_call(client,monkeypatch,tmp_path):
    from api.routes import diagnostics
    asset=_seed_faa_asset(client.app)
    calls=[]
    class Model(_LiveGroq):
        def chat(self,*args,**kwargs):
            calls.append(1)
            return super().chat(*args,**kwargs)
    client.app.state.groq_service=Model('Hydraulic pump leak at seal SWIA2025091876593.')
    monkeypatch.delenv('PYTEST_CURRENT_TEST')
    monkeypatch.setattr(diagnostics,'_cache_path',lambda:tmp_path/'cache.json')
    payload={'asset_id':asset,'symptom_text':'hydraulic leak'}
    first=client.post('/api/maintenance/diagnose',json=payload).json()
    client.app.state.settings.SESSION_GROUNDING_FILE=settings_file(tmp_path)
    second=client.post('/api/maintenance/diagnose',json=payload).json()
    assert len(calls)==1 and first['explanation']==second['explanation']
    assert first['grounding']['sentences'][0]['level']=='unrated'
    assert second['grounding']['sentences'][0]['level']=='supported'
    assert second['grounding']['configuration']['status']=='experimental'


def test_session_stores_and_replays_exact_grounding_after_source_and_settings_change(environment,tmp_path):
    client,app,settings,_,headers,asset=environment
    settings.SESSION_GROUNDING_FILE=settings_file(tmp_path)
    row=create(client,headers['owner'],asset)
    url=f"/api/sessions/{row['id']}"
    response=client.post(url+'/turns',json={'message':'hydraulic pump leak'},headers=headers['owner'])
    assert response.status_code==200,response.text
    result=response.json()
    assert result['grounding']['sentences'] and result['grounding']['configuration']['status']=='experimental'
    from sqlalchemy import select
    from db.models.sessions import SessionTurn
    with app.state.rel_store.session_scope() as db:
        saved=db.scalar(select(SessionTurn).where(SessionTurn.session_id==row['id']))
        assert json.loads(saved.grounding_json)==result['grounding']
    app.state.graph_repo.update_service_record('AALA2024050500004',{'text':'CHANGED AFTER SAVED CHECK'})
    settings.SESSION_GROUNDING_FILE='/missing/new-file'
    assert client.get(url,headers=headers['owner']).json()['turns'][0]['response']==result
    failed=client.post(url+'/turns',json={'message':'new observation'},headers=headers['owner'])
    assert failed.status_code==503
    assert client.get(url,headers=headers['owner']).json()['turn_count']==1


def test_blended_thresholds_are_not_reused_after_encoder_failure_or_on_structured_answers(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from investigation import embed_port
    settings=SimpleNamespace(SESSION_GROUNDING_FILE=settings_file(tmp_path,weight=.5))
    def forbidden(texts):raise AssertionError('No encoder/model call on structured answers')
    monkeypatch.setattr(embed_port,'embed_texts',forbidden)
    report=[{'record_id':'AALA2024010100001','part_name':'PUMP','text':'Pump cracked.'}]
    audit=annotate('Pump cracked AALA2024010100001.',report,settings,structured_answer=True)
    assert audit['checked_with']=='lexical' and audit['status']=='fallback_thresholds_pending'
    assert audit['sentences'][0]['level']=='unrated'
    ordinary=annotate('Pump cracked AALA2024010100001.',report,settings)
    assert ordinary['embedding_status']=='failed:AssertionError' and ordinary['sentences'][0]['level']=='unrated'


def test_bad_selected_configuration_fails_without_inventing_grounding(tmp_path):
    from types import SimpleNamespace
    from fastapi import HTTPException
    path=tmp_path/'bad.json';path.write_text(json.dumps({'status':'selected','parameters':{}}))
    with pytest.raises(HTTPException) as error:
        annotate('Pump cracked.',[],SimpleNamespace(SESSION_GROUNDING_FILE=str(path)))
    assert error.value.status_code==503


def test_grounding_configuration_is_frozen_before_inference(environment,tmp_path,monkeypatch):
    import investigation.sessions as module
    from pathlib import Path
    client,_,settings,_,headers,asset=environment
    settings.SESSION_GROUNDING_FILE=settings_file(tmp_path)
    original=module.run_turn
    calls=[]
    def change_config(**kwargs):
        calls.append(1)
        response=original(**kwargs)
        Path(settings.SESSION_GROUNDING_FILE).write_text('{invalid after inference starts')
        return response
    monkeypatch.setattr(module,'run_turn',change_config)
    row=create(client,headers['owner'],asset);url=f"/api/sessions/{row['id']}"
    result=client.post(url+'/turns',json={'message':'pump leak'},headers=headers['owner'])
    assert result.status_code==200,result.text
    assert result.json()['grounding']['configuration']['status']=='experimental'
    assert client.post(url+'/turns',json={'message':'pump leak'},headers=headers['owner']).status_code==503
    assert len(calls)==1


def test_deterministic_diagnose_uses_its_actual_displayed_source_boundary():
    from investigation.grounding_runtime import annotate_diagnose
    sources=[{'record_id':f'REC2024000000{i:02d}','text':'Pump leaked.','part_name':'PUMP'} for i in range(8)]
    context={'asset_history':sources,'fleet_matches':[]}
    response={'explanation':None,'fallback_explanation':f"Pump leaked [{sources[-1]['record_id']}].",
              'llm_status':'unavailable','evidence':[{'record_id':r['record_id']} for r in sources]}
    audited=annotate_diagnose(response,context,[],None)
    assert audited['grounding']['sentences'][0]['level']=='unrated'
    assert len(audited['grounding']['evidence'])==8
    # The identical citation outside a model's bounded prompt remains invalid.
    response.update(explanation=response['fallback_explanation'],llm_status='live')
    model=annotate_diagnose(response,context,[],None)
    assert model['grounding']['sentences'][0]['level']=='unsupported'
