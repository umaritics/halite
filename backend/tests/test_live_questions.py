"""Durable question/answer flow with actual ranking, JWTs and both SQL backends."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
import threading

from fastapi import HTTPException
import pytest

from investigation.attributes import load_codebook
from investigation.live_questions import QuestionController, visible_likelihoods
from tests.test_investigation_sessions import environment, create  # shared real-DB fixture
from tests.test_api_copilot import FakeCopilotLlm


def policy():
    # Synthetic test/demo operating point, deliberately not a selected research result.
    return {'status':'experimental','selection_year':2024,'ranker_version':'mid_heuristic-v1',
            'parameters':{'tau_answer':1.0,'g_min':.000001,'n_min':2,'max_questions':3}}


@pytest.fixture
def configured(environment, tmp_path):
    client, app, settings, users, headers, asset = environment
    path = tmp_path / 'synthetic-policy.json'
    path.write_text(json.dumps(policy()))
    settings.SESSION_QUESTIONS_ENABLED = True
    settings.SESSION_POLICY_FILE = str(path)
    repo = app.state.graph_repo
    tail = next(a['tail_number'] for a in repo.list_assets_with_counts() if a['id'] == asset)
    for i in range(40):
        repo.create_service_record({'record_id':f'QTEST20230101{i:05}', 'asset_key':tail,
                                   'occurred_at':'2023-01-01','submitted_at':'2023-01-02T00:00:00Z',
                                   'part_name':'PUMP' if i < 20 else 'SENSOR',
                                   'stage_of_operation':'CL' if i < 20 else 'CR',
                                   'how_discovered':'V' if i < 20 else 'C',
                                   'nature_of_condition':'K' if i < 20 else 'I',
                                   'precautionary_procedure':'K' if i < 20 else 'F',
                                   'text':'hydraulic pressure loss','status':'auto_accepted'})
        repo.link_record_about_asset(f'QTEST20230101{i:05}', asset)
    yield client, app, settings, users, headers, asset


def first_question(env):
    client, app, settings, users, headers, asset = env
    row = create(client, headers['owner'], asset)
    url = f"/api/sessions/{row['id']}"
    response = client.post(url+'/turns', json={'message':'hydraulic pressure loss'}, headers=headers['owner'])
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['decision'] == 'ask', result
    assert result['question']['id']
    assert result['question']['gain_bits'] > 0
    assert result['policy_status'] == 'experimental'
    assert result['beliefs']['calibrated'] is True and result['beliefs']['label'] == 'relative support'
    assert result['case_state']['question_state']['likelihood_audit']['invalid_or_missing_submission_time'] > 0
    return url, result


def answer_payload(result, value=None):
    question = result['question']
    return {'message':f"Answer to {question['attribute']}", 'answer':{'attribute':question['attribute'],
            'value':value or question['options'][0]['value'], 'question_id':question['id']}}


def test_question_answer_uses_saved_model_without_graph_or_llm_and_replays(configured, monkeypatch):
    client, app, _, _, headers, _ = configured
    url, initial = first_question(configured)
    def forbidden(*args, **kwargs):
        raise AssertionError('Structured answer must use only its durable snapshot')
    monkeypatch.setattr(app.state.graph_repo, 'list_service_records', forbidden)
    monkeypatch.setattr(app.state.graph_repo, 'list_assets_with_counts', forbidden)
    monkeypatch.setattr(app.state.graph_repo, 'get_service_record', forbidden)
    monkeypatch.setattr(app.state.groq_service, 'chat', forbidden)
    response = client.post(url+'/turns', json=answer_payload(initial), headers=headers['owner'])
    assert response.status_code == 200, response.text
    answered = response.json()
    transition = answered['belief_transition']
    assert transition['prior'] == initial['beliefs']
    assert transition['posterior'] == answered['beliefs']
    assert answered['beliefs'] != initial['beliefs']
    assert answered['evidence'] == initial['evidence']
    assert answered['llm_status'] == 'not_needed'
    assert len(answered['case_state']['question_state']['answers']) == 1
    assert answered['question']['attribute'] != initial['question']['attribute']
    saved = client.get(url, headers=headers['owner']).json()
    assert saved['turns'][0]['response'] == initial
    assert saved['turns'][1]['response'] == answered
    assert saved['turns'][1]['snapshot']['hypotheses'] == answered['beliefs']['hypotheses']
    assert saved['turns'][1]['snapshot']['belief_entropy'] == answered['beliefs']['entropy']


def test_not_sure_excludes_attribute_budget_is_durable_and_fourth_answer_rejected(configured):
    client, _, _, _, headers, _ = configured
    url, result = first_question(configured)
    seen = set()
    initial_beliefs = result['beliefs']
    for number in range(3):
        assert result['decision'] == 'ask'
        assert result['question']['attribute'] not in seen
        seen.add(result['question']['attribute'])
        response = client.post(url+'/turns', json=answer_payload(result,'not_sure'), headers=headers['owner'])
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['beliefs'] == initial_beliefs
        assert len(result['case_state']['question_state']['answers']) == number+1
    assert result['decision'] == 'abstain' and result['question'] is None
    assert result['policy_inputs']['questions_asked'] == 3
    assert 'qualified supervisor' in result['reply']
    response = client.post(url+'/turns', json={'message':'Old answer','answer':{'attribute':next(iter(seen)),'value':'not_sure'}}, headers=headers['owner'])
    assert response.status_code == 409
    # A free-text observation does not reset the three-question budget.
    fresh = client.post(url+'/turns',json={'message':'Another pressure observation'},headers=headers['owner'])
    assert fresh.status_code == 200, fresh.text
    assert fresh.json()['policy_inputs']['questions_asked'] == 3 and fresh.json()['question'] is None


def test_stale_unoffered_and_unowned_answers_do_not_create_turns(configured):
    client, _, _, _, headers, _ = configured
    url, first = first_question(configured)
    payload = answer_payload(first, 'invented-answer')
    assert client.post(url+'/turns',json=payload,headers=headers['owner']).status_code == 422
    payload = answer_payload(first)
    for key in ('question_id', 'attribute'):
        bad = deepcopy(payload)
        bad['answer'][key] = 'wrong'
        assert client.post(url+'/turns',json=bad,headers=headers['owner']).status_code == 409
    assert client.post(url+'/turns',json=payload,headers=headers['other']).status_code == 404
    assert client.post(url+'/turns',json=payload,headers=headers['supervisor']).status_code == 403
    accepted = client.post(url+'/turns',json=payload,headers=headers['owner'])
    assert accepted.status_code == 200
    assert client.post(url+'/turns',json=payload,headers=headers['owner']).status_code == 409
    assert client.get(url,headers=headers['owner']).json()['turn_count'] == 2


def test_concurrent_answers_claim_only_one_posterior(configured, monkeypatch):
    client, _, _, _, headers, _ = configured
    url, first = first_question(configured)
    barrier = threading.Barrier(2)
    original = QuestionController.answer
    def simultaneous(self, *args):
        response = original(self, *args)
        barrier.wait(timeout=10)
        return response
    monkeypatch.setattr(QuestionController, 'answer', simultaneous)
    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(lambda _: client.post(url+'/turns',json=answer_payload(first),headers=headers['owner']), range(2)))
    assert sorted(r.status_code for r in responses) == [200,409]
    saved = client.get(url,headers=headers['owner']).json()
    assert saved['turn_count'] == 2
    assert len(saved['turns'][1]['response']['case_state']['question_state']['answers']) == 1


def test_failed_snapshot_rolls_back_answer_and_question_consumption(configured, monkeypatch):
    import investigation.sessions as module
    client, _, _, _, headers, _ = configured
    url, first = first_question(configured)
    original = module.SessionSnapshot
    def failure(**kwargs):
        raise RuntimeError('synthetic snapshot failure')
    monkeypatch.setattr(module, 'SessionSnapshot', failure)
    with pytest.raises(RuntimeError,match='synthetic snapshot failure'):
        client.post(url+'/turns',json=answer_payload(first),headers=headers['owner'])
    monkeypatch.setattr(module, 'SessionSnapshot', original)
    saved = client.get(url,headers=headers['owner']).json()
    assert saved['turn_count'] == 1 and saved['turns'][0]['response'] == first
    assert client.post(url+'/turns',json=answer_payload(first),headers=headers['owner']).status_code == 200


def test_configuration_failure_is_explicit_without_affecting_frozen_stateless_route(configured):
    client, _, settings, _, headers, asset = configured
    settings.SESSION_POLICY_FILE = '/missing/policy.json'
    row = create(client,headers['owner'],asset)
    url=f"/api/sessions/{row['id']}"
    assert client.post(url+'/turns',json={'message':'pressure loss'},headers=headers['owner']).status_code == 503
    assert client.get(url,headers=headers['owner']).json()['turn_count'] == 0
    legacy=client.post('/api/maintenance/copilot/turn',json={'asset_id':asset,'message':'pressure loss'},headers=headers['owner'])
    assert legacy.status_code == 200 and legacy.json()['policy_status'] == 'not_configured'
    assert legacy.json()['beliefs']['calibrated'] is False and legacy.json()['reply'] is None


def test_model_cannot_choose_the_question_and_prose_questions_are_rejected(configured):
    client, app, _, _, headers, asset = configured
    llm = FakeCopilotLlm(reply='What test would you like to perform?')
    app.state.groq_service = llm
    url, result = first_question(configured)
    assert result['explanation_source'] == 'template' and '?' not in result['reply']
    assert any('unrequested model-written question' in w for w in result['warnings'])
    assert result['question']['attribute'] in load_codebook()['attributes'] or result['question']['attribute'] in result['case_state']['question_state']['models']


def test_temporal_visibility_chain_exclusion_and_model_scope_are_audited(graph_repo_empty):
    repo=graph_repo_empty
    asset=repo.find_or_create_asset('N1',{'make':'M','model':'ONE'})
    for rid,submitted,text in [('ANCEST01','2023-01-01T00:00:00Z','leak'),
                               ('QUERY001','2023-02-01T00:00:00Z','SUPPLEMENTAL REPORT FOR (ANCEST01)'),
                               ('LATER001','2023-03-01T00:00:00Z','SUPPLEMENTAL REPORT FOR (QUERY001)'),
                               ('EQUAL001','2023-04-01T00:00:00Z','leak'),
                               ('BADTIME1','04/01/2023','leak'),
                               ('VISIBLE1','2023-01-01T00:00:00Z','pressure')]:
        repo.create_service_record({'record_id':rid,'asset_key':'N1','occurred_at':'2023-01-01','submitted_at':submitted,
                                    'text':text,'part_name':'PUMP','stage_of_operation':'CL'})
    controller=QuestionController(policy())
    models,audit=visible_likelihoods(repo,['PUMP'],controller.schema,asset_id=asset['id'],message='Investigate QUERY001',
                                     now=datetime(2023,4,1,tzinfo=timezone.utc))
    assert audit['n_visible_records'] == 1
    assert audit['excluded_chain_record_ids'] == ['ANCEST01','LATER001','QUERY001']
    assert audit['equal_or_future_records'] == 1 and audit['invalid_or_missing_submission_time'] == 1
    assert models['stage_of_operation']['fleet_n'] == 1


def test_policy_version_and_selected_point_provenance_are_required():
    for bad in ({**policy(),'selection_year':2025}, {**policy(),'status':'selected'}, {**policy(),'parameters':{**policy()['parameters'],'n_min':1}}):
        with pytest.raises(ValueError):
            QuestionController(bad)


def test_live_snapshot_applies_time_before_limits_and_reverses_only_future_supersession(graph_repo_empty):
    from investigation.live_graph import LiveGraphSnapshot
    repo=graph_repo_empty
    asset=repo.find_or_create_asset('N1')
    for rid,date,submitted,text,status in [
        ('PAST0001','2023-01-01','2023-01-01T00:00:00Z','pressure loss','superseded'),
        ('FUTURE01','2023-06-01','2023-06-01T00:00:00Z','SUPPLEMENTAL REPORT FOR (PAST0001)','unscored'),
        ('NOABOUT1','2023-01-01','2023-01-01T00:00:00Z','orphan','unscored'),
        ('BADTIME1','2023-05-01','05/01/2023','pressure','unscored')]:
        repo.create_service_record({'record_id':rid,'asset_key':'N1','occurred_at':date,'submitted_at':submitted,
                                    'text':text,'part_name':'PUMP','status':status})
        if rid != 'NOABOUT1':
            repo.link_record_about_asset(rid,asset['id'])
    snap=LiveGraphSnapshot(repo,now=datetime(2023,4,1,tzinfo=timezone.utc),asset_id=asset['id'])
    recent=snap.list_asset_history_recent(asset['id'],limit=1)
    assert [r['record_id'] for r in recent] == ['PAST0001']
    assert recent[0]['status'] == 'unscored' and recent[0]['is_superseded'] is False
    assert snap.get_service_record('FUTURE01') is None and snap.get_service_record('BADTIME1') is None
    assert snap.invalid == 1
    assert snap.get_service_records_by_ids(['FUTURE01','PAST0001']) == recent
    later=LiveGraphSnapshot(repo,now=datetime(2023,7,1,tzinfo=timezone.utc),asset_id=asset['id'])
    assert later.get_service_record('PAST0001')['status'] == 'superseded'
    assert repo.get_service_record('PAST0001')['status'] == 'superseded'  # snapshot does not mutate graph


def test_empty_visible_history_abstains_without_inventing_a_question(configured):
    client, app, _, _, headers, asset = configured
    for row in app.state.graph_repo.list_service_records():
        app.state.graph_repo.update_service_record(row['record_id'],{'submitted_at':'2099-01-01T00:00:00Z'})
    row=create(client,headers['owner'],asset)
    response=client.post(f"/api/sessions/{row['id']}/turns",json={'message':'pressure loss'},headers=headers['owner'])
    assert response.status_code == 200, response.text
    result=response.json()
    assert result['decision'] == 'abstain' and result['question'] is None
    assert not result['ranked_checks'] and not result['evidence']
    assert result['beliefs']['other'] == 1


def test_saved_question_survives_application_restart_and_uses_its_saved_policy(configured):
    from fastapi.testclient import TestClient
    from tests.conftest import _build_test_app
    client, _, settings, _, headers, _ = configured
    url, first=first_question(configured)
    # New service configuration must not change the meaning of an already saved answer.
    changed=policy()
    changed['parameters']['tau_answer']=0
    from pathlib import Path
    Path(settings.SESSION_POLICY_FILE).write_text(json.dumps(changed))
    restarted=_build_test_app(settings)
    with TestClient(restarted) as fresh:
        assert fresh.get(url,headers=headers['owner']).json()['turns'][0]['response'] == first
        def forbidden(*args,**kwargs):
            raise AssertionError('A saved answer must not read new graph data after restart')
        restarted.state.graph_repo.list_service_records=forbidden
        response=fresh.post(url+'/turns',json=answer_payload(first,'not_sure'),headers=headers['owner'])
        assert response.status_code == 200, response.text
        answered=response.json()
        assert answered['policy_inputs']['parameters']['tau_answer'] == 1.0
        assert answered['policy_provenance'] == first['policy_provenance']
        assert answered['decision'] == 'ask'
    restarted.state.rel_store.close()


def test_free_text_replaces_question_identity_and_retains_answered_attribute_exclusion(configured):
    client, _, _, _, headers, _ = configured
    url, first=first_question(configured)
    new=client.post(url+'/turns',json={'message':'hydraulic pressure loss still observed'},headers=headers['owner'])
    assert new.status_code == 200, new.text
    replaced=new.json()
    assert replaced['question']['id'] != first['question']['id']
    assert client.post(url+'/turns',json=answer_payload(first),headers=headers['owner']).status_code == 409
    answered=client.post(url+'/turns',json=answer_payload(replaced,'not_sure'),headers=headers['owner']).json()
    after=client.post(url+'/turns',json={'message':'hydraulic pressure loss again'},headers=headers['owner'])
    assert after.status_code == 200, after.text
    state=after.json()['case_state']['question_state']
    assert state['answers'] == answered['case_state']['question_state']['answers']
    if after.json()['question']:
        assert after.json()['question']['attribute'] != replaced['question']['attribute']


def test_closure_during_answer_does_not_commit_posterior(configured, monkeypatch):
    client, _, _, _, headers, _ = configured
    url, first=first_question(configured)
    original=QuestionController.answer
    def close_first(self,*args):
        response=original(self,*args)
        closed=client.post(url+'/close',json={'outcome_note':'Synthetic closure race fixture'},headers=headers['owner'])
        assert closed.status_code == 200
        return response
    monkeypatch.setattr(QuestionController,'answer',close_first)
    response=client.post(url+'/turns',json=answer_payload(first),headers=headers['owner'])
    assert response.status_code == 409
    saved=client.get(url,headers=headers['owner']).json()
    assert saved['status'] == 'closed' and saved['turn_count'] == 1
    assert saved['turns'][0]['response'] == first


def test_healthy_model_prose_uses_saved_evidence_allow_list(configured):
    client, app, _, _, headers, asset = configured
    _, first=first_question(configured)
    allowed=first['evidence'][0]['record_id']
    app.state.groq_service=FakeCopilotLlm(reply=f'Report {allowed} records hydraulic pressure loss.')
    row=create(client,headers['owner'],asset)
    response=client.post(f"/api/sessions/{row['id']}/turns",json={'message':'hydraulic pressure loss'},headers=headers['owner'])
    assert response.status_code == 200, response.text
    result=response.json()
    assert result['explanation_source'] == 'model' and result['llm_status'] == 'available'
    assert result['citation_validation'] == {'valid_ids':[allowed],'invalid_ids':[],'all_valid':True}
    assert result['prose_context']['accepted_as_reply'] is True
    answered = client.post(f"/api/sessions/{row['id']}/turns", json=answer_payload(result), headers=headers['owner'])
    assert answered.status_code == 200, answered.text
    assert 'prose_context' not in answered.json()
    assert answered.json()['llm_status'] == 'not_needed'
    app.state.groq_service=FakeCopilotLlm(reply='Report SWIA2024010100001 states a crack.')
    row=create(client,headers['owner'],asset)
    invalid=client.post(f"/api/sessions/{row['id']}/turns",json={'message':'pressure loss'},headers=headers['owner']).json()
    assert invalid['citation_validation']['invalid_ids'] == ['SWIA2024010100001']
    assert '[UNVERIFIED:SWIA2024010100001]' in invalid['reply']


def test_answer_priority_report_mode_and_ranker_mismatch_are_explicit(configured):
    from pathlib import Path
    client, _, settings, _, headers, asset = configured
    chosen=policy()
    chosen['parameters']['tau_answer']=0
    Path(settings.SESSION_POLICY_FILE).write_text(json.dumps(chosen))
    row=create(client,headers['owner'],asset)
    result=client.post(f"/api/sessions/{row['id']}/turns",json={'message':'pressure loss'},headers=headers['owner'])
    assert result.status_code == 200, result.text
    assert result.json()['decision'] == 'answer' and result.json()['question'] is None
    assert result.json()['policy_inputs']['evidence_count'] >= 2
    row=create(client,headers['owner'],asset)
    report=client.post(f"/api/sessions/{row['id']}/turns",json={'message':'Summarize QTEST2023010100039'},headers=headers['owner'])
    assert report.status_code == 200, report.text
    assert report.json()['decision'] == 'report' and report.json()['question'] is None
    chosen['ranker_version']='different-version'
    Path(settings.SESSION_POLICY_FILE).write_text(json.dumps(chosen))
    row=create(client,headers['owner'],asset)
    url=f"/api/sessions/{row['id']}"
    assert client.post(url+'/turns',json={'message':'pressure loss'},headers=headers['owner']).status_code == 503
    assert client.get(url,headers=headers['owner']).json()['turn_count'] == 0
