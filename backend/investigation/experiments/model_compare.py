"""Resumable Ollama comparison with raw responses, exact identities and no fallback.

Uses only the Python standard library and the pure lexical checker. It does not
install/pull models, choose a model, or change application configuration.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import statistics
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler

from investigation.grounding import GroundingParameters,check_reply
from investigation.experiments.model_prompts import FACT_KEYS,VERSION,fingerprint,messages

VERSION_RUN='interactive-model-comparison-v1'


def now():return datetime.now(timezone.utc).isoformat()


def hardware():
    data={'system':platform.system(),'machine':platform.machine(),'release':platform.release()}
    if data['system']=='Darwin':
        for field,key in [('chip','machdep.cpu.brand_string'),('memory_bytes','hw.memsize')]:
            value=subprocess.check_output(['sysctl','-n',key],text=True,timeout=10).strip()
            data[field]=int(value) if field=='memory_bytes' else value
    return data


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class Ollama:
    def __init__(self,url,*,timeout=180,token=None):
        parsed=urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Use a plain HTTP(S) Ollama base URL without embedded credentials/query/fragment.')
        if parsed.scheme=='http' and parsed.hostname not in ('localhost','127.0.0.1','::1'):
            raise ValueError('Remote endpoints require HTTPS or a loopback SSH tunnel.')
        if not math.isfinite(timeout) or timeout<=0:raise ValueError('Positive finite timeout required.')
        self.url=url.rstrip('/');self.timeout=timeout;self.token=token
        self.local=parsed.hostname in ('localhost','127.0.0.1','::1')
        self.opener=build_opener(NoRedirect)

    def request(self,path,payload=None):
        headers={'Content-Type':'application/json'}
        if self.token:headers['Authorization']='Bearer '+self.token
        request=Request(self.url+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        with self.opener.open(request,timeout=self.timeout) as response:
            raw=response.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise ValueError('Provider response exceeds the declared four MiB limit.')
            result=json.loads(raw)
        if not isinstance(result,dict):raise ValueError('Provider returned a non-object response.')
        if result.get('error'):raise RuntimeError('Provider returned an explicit error.')
        return result

    def identity(self,model):
        found=[r for r in self.request('/api/tags').get('models',[]) if r.get('name')==model]
        if len(found)!=1 or not found[0].get('digest'):raise ValueError('Exact installed model name/digest required; no automatic model pull.')
        row=found[0]
        return {k:row.get(k) for k in ('name','digest','size','details')}

    def chat(self,model,prompt,*,json_mode=False,seed=1729):
        if sum(len(message['content'].encode()) for message in prompt)>3200:
            raise ValueError('Prompt exceeds the frozen conservative context budget; no silent truncation.')
        payload={'model':model,'messages':prompt,'stream':False,'keep_alive':'5m',
                 'options':{'temperature':0,'seed':seed,'num_predict':700,'num_ctx':4096}}
        if json_mode:payload['format']='json'
        return self.request('/api/chat',payload)


def load_packet(path):
    data=json.loads(Path(path).read_text())
    digest=data.get('packet_sha256')
    if data.get('version')!=VERSION or fingerprint({k:v for k,v in data.items() if k!='packet_sha256'})!=digest:
        raise ValueError('Prompt packet version/fingerprint mismatch.')
    cases=data['cases']
    if len(cases)!=20 or len({c['case_id'] for c in cases})!=20 or Counter(c['task'] for c in cases)!=Counter({'facts':10,'prose':10}):
        raise ValueError('Exactly twenty unique prompts, ten facts and ten prose, required.')
    if data.get('held_out_2025_used') is not False or any(c['year']!=2024 for c in cases):
        raise ValueError('This selection runner must not use held-out 2025.')
    for c in cases:
        if not c['observation'].strip() or not c['evidence'] or len({r['record_id'] for r in c['evidence']})!=len(c['evidence']):
            raise ValueError('Observation and unique evidence sources required.')
        if sum(len(m['content'].encode()) for m in messages(c))>3200:
            raise ValueError('Frozen prompt exceeds the declared context budget.')
    return data


def load_parameters(path):
    if not path:return None,None
    raw=Path(path).read_bytes();data=json.loads(raw)
    if data.get('status') not in ('experimental','selected'):raise ValueError('Explicit checker status required.')
    if data['status']=='selected' and not (data.get('label_result_sha256') and data.get('decision_reference')):
        raise ValueError('Selected checker needs human-label and decision references.')
    params=GroundingParameters(**data['parameters'])
    if params.lexical_weight!=1:raise ValueError('Portable comparison currently requires lexical calibration, not an unavailable dense encoder.')
    return params,{'sha256':hashlib.sha256(raw).hexdigest(),'status':data['status'],
                   'label_result_sha256':data.get('label_result_sha256'),'decision_reference':data.get('decision_reference')}


def assess(raw,case,*,baseline=False,parameters=None):
    message=raw.get('message')
    content=message.get('content') if isinstance(message,dict) else None
    complete=raw.get('done') is True and raw.get('done_reason') not in ('length','max_tokens')
    valid=isinstance(content,str) and bool(content.strip()) and complete
    reason=None
    if case['task']=='facts':
        try:
            facts=json.loads(content)
            valid=valid and isinstance(facts,dict) and set(facts)==set(FACT_KEYS) and all(isinstance(v,list) and all(isinstance(s,str) for s in v) for v in facts.values())
        except (ValueError,TypeError):valid=False
        reason=None if valid else 'Incomplete, empty or invalid strict fact JSON.'
        return {'valid_output':valid,'invalid_reason':reason,'grounding':None}
    valid=valid and not any(q in (content or '') for q in '?？؟')
    reason=None if valid else 'Incomplete/empty prose or a model-written question.'
    # L2 follows the generation boundary. The no-evidence arm cannot be credited
    # for a guessed matching ID that was never supplied to the model.
    audit=check_reply(content if isinstance(content,str) else '',[] if baseline else case['evidence'],parameters=parameters)
    sentences=audit['sentences'];citations=[rid for s in sentences for rid in s['citations']]
    good=sum(len(s['valid_citations']) for s in sentences)
    unvalidated=sum(s['level']=='unrated' for s in sentences)
    unsupported=sum(s['level']=='unsupported' or (s['level']=='uncited' and not s['acceptable_uncited']) for s in sentences)
    return {'valid_output':valid,'invalid_reason':reason,'grounding':audit,'citation_occurrences':len(citations),
            'in_evidence_citation_occurrences':good,'sentence_count':len(sentences),'unrated_sentences':unvalidated,
            'unsupported_or_unapproved_uncited_sentences':unsupported,
            'unsupported_rate':unsupported/len(sentences) if parameters is not None and sentences and not unvalidated else None}


def summarize(rows):
    summaries=[]
    groups=sorted({(r['model'],r['arm'],r['task']) for r in rows})
    for model,arm,task in groups:
        selected=[r for r in rows if (r['model'],r['arm'],r['task'])==(model,arm,task)]
        successful=[r for r in selected if not r.get('error')]
        measured=[r['assessment'] for r in successful]
        citations=sum(r.get('citation_occurrences',0) for r in measured)
        sentences=sum(r.get('sentence_count',0) for r in measured)
        unrated=sum(r.get('unrated_sentences',0) for r in measured)
        summaries.append({'model':model,'arm':arm,'task':task,'n_attempted':len(selected),'n_responses':len(successful),
                          'valid_output_share':sum(r['valid_output'] for r in measured)/len(selected),
                          'citation_occurrences':citations,
                          'in_evidence_citation_share':sum(r.get('in_evidence_citation_occurrences',0) for r in measured)/citations if citations else None,
                          'sentence_count':sentences,'unrated_sentences':unrated,
                          'unsupported_or_unapproved_uncited_sentences':sum(r.get('unsupported_or_unapproved_uncited_sentences',0) for r in measured),
                          'unsupported_rate':sum(r.get('unsupported_or_unapproved_uncited_sentences',0) for r in measured)/sentences if sentences and not unrated and len(successful)==len(selected) and all(r['grounding'] and r['grounding']['parameters'] is not None for r in measured) else None,
                          'seconds_per_attempt_mean':statistics.mean(r['wall_seconds'] for r in selected),
                          'seconds_per_response_median':statistics.median(r['wall_seconds'] for r in successful) if successful else None})
    return summaries


def append(path,row):
    with path.open('a') as stream:
        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())


def read_rows(path):
    if not path.exists():return []
    raw=path.read_bytes()
    if raw and not raw.endswith(b'\n'):raise ValueError('Incomplete journal tail: preserve it and repair explicitly; never silently discard a response.')
    return [json.loads(line) for line in raw.splitlines()]


def run(packet,models,output,*,endpoint='http://127.0.0.1:11434',role='development',grounding=None,resume=False,timeout=180,client=None):
    data=load_packet(packet);params,checker=load_parameters(grounding)
    if len(models)!=len(set(models)) or not 1<=len(models)<=4:raise ValueError('One to four distinct installed models required.')
    if role not in ('development','m4_comparison','staging_reference'):raise ValueError('Unknown measurement role.')
    transport=client or Ollama(endpoint,timeout=timeout,token=os.getenv('HALITE_MODEL_API_KEY'))
    machine=hardware()
    server_version=transport.request('/api/version').get('version')
    if not isinstance(server_version,str) or not server_version.strip():raise ValueError('Ollama server version is required.')
    if role=='m4_comparison' and (not transport.local or machine.get('system')!='Darwin' or machine.get('machine')!='arm64' or 'Apple M4' not in machine.get('chip','') or not 2<=len(models)<=3):
        raise ValueError('M4 comparison requires execution on an Apple M4 with a loopback endpoint and two or three models. A tunnel alone does not prove server hardware.')
    if role=='staging_reference' and (len(models)!=1 or not models[0].startswith('phi4-mini')):
        raise ValueError('Staging reference is one exact installed phi4-mini model.')
    identities={model:transport.identity(model) for model in models}
    if role=='m4_comparison':
        for identity in identities.values():
            size=re.fullmatch(r'(\d+(?:\.\d+)?)B',str((identity.get('details') or {}).get('parameter_size','')).strip())
            if not size or not 7<=float(size[1])<9:
                raise ValueError('M4 candidate comparison requires verified 7–8B installed-model details; keep phi4-mini in the separate reference run.')
    source=Path(__file__)
    methods=[source,source.with_name('model_prompts.py'),source.parent.parent/'grounding.py',source.parent.parent/'data/grounding_parts_v1.json']
    plan={'version':VERSION_RUN,'packet_sha256':data['packet_sha256'],'models':models,'model_identities':identities,
          'endpoint':transport.url,'server_version':server_version,'execution_source':'injected_test_client' if client is not None else 'ollama_http','hardware':machine,'measurement_role':role,
          'server_hardware_verified':False,'hardware_note':'Hardware describes the runner; even loopback can be a tunnel. Verify server placement before model selection.',
          'checker':checker,'seed':1729,'timeout_seconds':timeout,'generation':{'temperature':0,'num_predict':700,'num_ctx':4096,'keep_alive':'5m'},
          'method_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in methods},
          'protocol':'One warmup per model excluded; serial primary and paired no-evidence prose calls in seeded arm order. No retries, fallback, model pull or automatic winner.'}
    directory=Path(output)
    if directory.exists():
        if not resume:raise FileExistsError('Use a fresh run directory or explicit --resume.')
        existing=json.loads((directory/'manifest.json').read_text())
        if existing['plan']!=plan:raise ValueError('Resume configuration, packet, model digest, machine or method changed.')
    else:
        if resume:raise FileNotFoundError('Cannot resume a missing run.')
        directory.mkdir(parents=True)
        (directory/'manifest.json').write_text(json.dumps({'started_at':now(),'plan':plan},indent=2)+'\n')
        (directory/'packet.json').write_bytes(Path(packet).read_bytes())
    journal=directory/'responses.jsonl';rows=read_rows(journal)
    keys=[(r['model'],r['case_id'],r['arm']) for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate journal response identity.')
    expected={(model,c['case_id'],arm) for model in models for c in data['cases'] for arm in (['evidence','no_evidence'] if c['task']=='prose' else ['evidence'])}
    if not set(keys)<=expected:raise ValueError('Foreign response in journal.')
    cases_by_id={c['case_id']:c for c in data['cases']}
    for row in rows:
        case=cases_by_id[row['case_id']]
        if row.get('task')!=case['task'] or row.get('prompt_sha256')!=fingerprint(messages(case,baseline=row['arm']=='no_evidence')):
            raise ValueError('Journal task or prompt fingerprint changed.')
        if type(row.get('wall_seconds')) not in (int,float) or not math.isfinite(row['wall_seconds']) or row['wall_seconds']<0:
            raise ValueError('Invalid journal timing.')
        if not row.get('error') and (row['raw'].get('model')!=row['model'] or row.get('assessment')!=assess(row['raw'],case,baseline=row['arm']=='no_evidence',parameters=params)):
            raise ValueError('Journal assessment differs from its raw response.')
    saved=set(keys)
    order=list(models);random.Random(1729).shuffle(order)
    for model in order:
        # Resume may occur after the server evicted a model. Rewarm each model
        # with pending work on every invocation; never count warmups as cases.
        if any(key[0]==model and key not in saved for key in expected):
            start=time.perf_counter()
            raw=transport.chat(model,[{'role':'user','content':'Reply with the word ready.'}])
            if raw.get('model')!=model or raw.get('done') is not True or not raw.get('message',{}).get('content'):
                raise ValueError('Warmup returned an incomplete response or a different model.')
            append(directory/'warmups.jsonl',{'model':model,'at':now(),'wall_seconds':time.perf_counter()-start,'raw':raw})
        for index,case in enumerate(data['cases']):
            arms=['evidence','no_evidence'] if case['task']=='prose' else ['evidence']
            random.Random(1729+index).shuffle(arms)
            for arm in arms:
                key=(model,case['case_id'],arm)
                if key in saved:continue
                prompt=messages(case,baseline=arm=='no_evidence');start=time.perf_counter()
                row={'model':model,'case_id':case['case_id'],'task':case['task'],'arm':arm,'at':now(),'prompt_sha256':fingerprint(prompt)}
                try:
                    raw=transport.chat(model,prompt,json_mode=case['task']=='facts')
                    row['raw']=raw
                    if raw.get('model')!=model:raise ValueError('Response model identity differs from the exact requested name.')
                    row['assessment']=assess(raw,case,baseline=arm=='no_evidence',parameters=params)
                except Exception as exc:
                    # Error types are auditable without leaking a token/URL/body.
                    row['error']=type(exc).__name__
                row['wall_seconds']=time.perf_counter()-start
                append(journal,row);rows.append(row);saved.add(key)
        if transport.identity(model)!=identities[model]:raise ValueError('Model digest/details changed during measurement; run is not final.')
    result={'version':VERSION_RUN,'completed_at':now(),'complete':saved==expected,'n_attempts':len(rows),'n_responses':sum(not r.get('error') for r in rows),'provider_errors':sum(bool(r.get('error')) for r in rows),'packet_sha256':data['packet_sha256'],
            'measurement_role':role,'held_out_2025_used':False,'checker':checker,'summaries':summarize(rows),'selected_model':None,
            'support_note':'Unsupported rate includes uncited non-whitelisted sentences; null if any cited sentence is unrated or a provider attempt failed. This is checker output, not human ground truth.',
            'hardware_note':plan['hardware_note'],'journal_sha256':hashlib.sha256(journal.read_bytes()).hexdigest()}
    (directory/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    write_table(directory/'COMPARISON.md',result,plan)
    return result


def write_table(path,result,plan):
    def show(value):return 'unavailable' if value is None else f'{value:.4f}'
    lines=['# Fixed-prompt interactive model comparison','',
           'Measurement role: `'+result['measurement_role']+'`. No model has been selected.',
           'Runner hardware: `'+json.dumps(plan['hardware'],sort_keys=True)+'`. '+plan['hardware_note'],
           'Data year: 2024; twenty primary prompts (ten fact extraction, ten prose) plus ten paired no-evidence prose calls per model.',
           'One warmup per active model/invocation excluded. Serial requests; latency includes provider load and network time.',
           'Raw responses and exact prompts are retained in the response journal and packet. Provider failures count against valid-output share.',
           'Checker status: '+(result['checker']['status'] if result['checker'] else 'thresholds pending; semantic support rates unavailable')+'.',
           '', '| Model | Arm | Task | Attempts | Responses | Valid output share | In-evidence citation share | Unsupported + uncited | Unsupported + uncited rate | Mean seconds / attempt | Median seconds / response |',
           '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in result['summaries']:
        lines.append('| '+' | '.join([row['model'],row['arm'],row['task'],str(row['n_attempted']),str(row['n_responses']),show(row['valid_output_share']),show(row['in_evidence_citation_share']),str(row['unsupported_or_unapproved_uncited_sentences']) if row['task']=='prose' else 'not applicable',show(row['unsupported_rate']),show(row['seconds_per_attempt_mean']),show(row['seconds_per_response_median'])])+' |')
    lines+=['',result['support_note'],'',
            'The no-evidence arm has an empty evidence list at generation and L2 assessment. Missing citations are observable citation failures; they are not proof of false aircraft facts. No human-ground-truth accuracy is claimed.',
            'Exact output-schema validity is not extraction accuracy. Report task-specific denominators and raw outputs when choosing the interactive model.',
            'No held-out 2025 data was used. No model winner or probability wording is inferred.']
    Path(path).write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('packet','output'):parser.add_argument('--'+key,required=True)
    parser.add_argument('--models',nargs='+',required=True);parser.add_argument('--endpoint',default='http://127.0.0.1:11434')
    parser.add_argument('--role',choices=['development','m4_comparison','staging_reference'],default='development')
    parser.add_argument('--grounding');parser.add_argument('--resume',action='store_true');parser.add_argument('--timeout',type=float,default=180)
    args=parser.parse_args();result=run(**vars(args));print(json.dumps({'complete':result['complete'],'responses':result['n_responses'],'provider_errors':result['provider_errors'],'selected_model':None}))
    if result['provider_errors']:raise SystemExit(2)
