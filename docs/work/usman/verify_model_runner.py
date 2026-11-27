"""Actual HTTP + extracted-bundle smoke, with explicitly synthetic provider output.

No real model, M4 timing, human label or semantic accuracy result is produced.
Run with system Python; no third-party package is imported.
"""
from collections import Counter
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import zipfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'))
from investigation.experiments.model_bundle import build
from investigation.experiments.model_compare import load_packet
from investigation.experiments.model_prompts import FACT_KEYS

packet=ROOT/'backend/investigation/experiments/data/model_prompts_2024_v1.json'
data=load_packet(packet)
assert len(data['cases'])==20 and Counter(c['task'] for c in data['cases'])=={'facts':10,'prose':10}
# Validate against original frozen sources, not only the packet's own assertions.
from investigation.experiments.offline import Corpus,OPEN,load_records
records,meta=load_records([ROOT/'backend/data/raw/usman_decision_2023.csv.gz',ROOT/'backend/data/raw/usman_decision_2024.csv.gz'])
assert meta==data['corpus']
corpus=Corpus(records)
for c in data['cases']:
    original=records[c['case_id']]
    assert c['observation']==OPEN.sub('',original['text']).strip()
    assert not {'answer_id','answer_part','answer_text'}&set(c)
    for r in c['evidence']:
        source=records[r['record_id']]
        assert source['submitted_at']<original['submitted_at']
        assert corpus.chains[source['record_id']]!=corpus.chains[original['record_id']]
        assert all(source[k]==r[k] for k in ('record_id','text','part_name'))
assert data['method_sha256']==hashlib.sha256((ROOT/'backend/investigation/experiments/model_prompts.py').read_bytes()).hexdigest()

requests=[]
fail_next_case=False
class SyntheticOllama(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,value):
        raw=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/version':self.respond({'version':'synthetic-http-fixture-not-ollama'})
        elif self.path=='/api/tags':self.respond({'models':[{'name':'synthetic-http:latest','digest':'synthetic-not-a-model','size':1,'details':{'source':'synthetic verification only'}}]})
        else:self.send_error(404)
    def do_POST(self):
        global fail_next_case
        assert self.path=='/api/chat'
        payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        requests.append(payload)
        assert payload['stream'] is False
        if payload['messages'][0]['content']=='Reply with the word ready.':content='ready'
        elif fail_next_case:
            fail_next_case=False
            self.send_error(503,'Synthetic provider outage');return
        elif payload.get('format')=='json':content=json.dumps({key:[] for key in FACT_KEYS})
        else:
            facts=json.loads(payload['messages'][-1]['content'].split('\n')[-1])
            content='No supplied history supports a diagnosis.' if not facts['evidence'] else 'Historical report ['+facts['evidence'][0]['record_id']+'].'
        self.respond({'model':payload['model'],'message':{'content':content},'done':True,'done_reason':'stop','eval_count':3,'total_duration':1000})

with tempfile.TemporaryDirectory(prefix='halite-synthetic-runner-') as tmp:
    tmp=Path(tmp);archive=tmp/'runner.zip'
    build(packet,archive,ROOT/'docs/work/usman/MODEL_COMPARISON_RUNNER.md')
    with zipfile.ZipFile(archive) as source:source.extractall(tmp/'runner')
    server=ThreadingHTTPServer(('127.0.0.1',0),SyntheticOllama);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    command=[sys.executable,'-I','-S',str(tmp/'runner/run_compare.py'),'--models','synthetic-http:latest',
             '--endpoint',f'http://127.0.0.1:{server.server_port}','--output',str(tmp/'results')]
    try:
        first=subprocess.run(command,capture_output=True,text=True,timeout=60)
        assert first.returncode==0,first.stderr
        result=json.loads((tmp/'results/results.json').read_text())
        assert result['complete'] and result['n_attempts']==30 and result['n_responses']==30
        assert result['measurement_role']=='development' and result['selected_model'] is None
        assert result['provider_errors']==0
        assert all(r['unsupported_rate'] is None for r in result['summaries'])
        assert len(requests)==31
        before=(tmp/'results/responses.jsonl').read_bytes()
        resumed=subprocess.run([*command,'--resume'],capture_output=True,text=True,timeout=60)
        assert resumed.returncode==0,resumed.stderr
        assert len(requests)==31 and (tmp/'results/responses.jsonl').read_bytes()==before
        manifest=json.loads((tmp/'results/manifest.json').read_text())
        assert manifest['plan']['execution_source']=='ollama_http'
        assert manifest['plan']['server_version']=='synthetic-http-fixture-not-ollama'
        assert manifest['plan']['server_hardware_verified'] is False
        fail_next_case=True
        failing=[str(tmp/'failed-results') if part==str(tmp/'results') else part for part in command]
        failure=subprocess.run(failing,capture_output=True,text=True,timeout=60)
        assert failure.returncode==2,failure.stderr
        failed=json.loads((tmp/'failed-results/results.json').read_text())
        assert failed['complete'] and failed['provider_errors']==1 and failed['n_attempts']==30 and failed['n_responses']==29
        proof={'source':'Synthetic HTTP protocol verification only; not a real model or M4 measurement',
               'python_isolated_no_site_packages':True,'real_packet_cases':20,'primary_prompts':20,'paired_no_evidence_prompts':10,
               'excluded_warmups':1,'http_chat_posts':31,'second_run_provider_error_kept_in_denominator':True,'provider_failure_cli_exit':failure.returncode,'responses_journaled':30,'exact_resume_without_extra_chat':True,
               'strict_temporal_and_chain_audit':True,'packet_sha256':data['packet_sha256'],
               'real_model_measurements':False,'selected_model':None}
        print(json.dumps(proof,indent=2))
    finally:server.shutdown();server.server_close();thread.join()
