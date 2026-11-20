"""Synthetic provider tests; never real model measurements or human labels."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import unittest
import tempfile
from unittest.mock import patch

from investigation.experiments import model_compare as mc
from investigation.experiments.model_prompts import FACT_KEYS,VERSION,fingerprint,messages
from investigation.experiments.model_bundle import build as bundle


def packet(tmp_path):
    cases=[{'case_id':f'SYNTHETIC{i}','year':2024,'task':'facts' if i%2==0 else 'prose',
            'observation':'Hydraulic pressure loss; no smoke.',
            'evidence':[{'record_id':f'REC20240000{i:02d}','text':'Pump leaked.','part_name':'PUMP','status':'auto_accepted'}]} for i in range(20)]
    value={'version':VERSION,'cases':cases,'held_out_2025_used':False}
    value['packet_sha256']=fingerprint(value)
    path=tmp_path/'synthetic-packet.json';path.write_text(json.dumps(value));return path


class SyntheticProvider:
    local=True
    url='http://127.0.0.1:11434'
    def __init__(self):self.calls=[];self.digest='synthetic-not-a-model';self.interrupt_at=None;self.error_at=None
    def request(self,*args):return {'version':'synthetic-test-server'}
    def identity(self,model):return {'name':model,'digest':self.digest,'size':1,'details':{'source':'synthetic'}}
    def chat(self,model,prompt,**options):
        self.calls.append((model,prompt,options))
        if len(self.calls)==self.interrupt_at:raise KeyboardInterrupt('Synthetic interruption')
        if len(self.calls)==self.error_at:raise TimeoutError('Synthetic timeout')
        if prompt[0]['content'].startswith('Reply with'):
            content='ready'
        elif options.get('json_mode'):
            content=json.dumps({key:[] for key in FACT_KEYS})
        else:
            payload=json.loads(prompt[-1]['content'].split('\n')[-1])
            content='Pump leaked ['+payload['evidence'][0]['record_id']+'].' if payload['evidence'] else 'No historical evidence was supplied.'
        return {'model':model,'message':{'content':content},'done':True,'done_reason':'stop','eval_count':8,'total_duration':1000}


class TestPortableComparison(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory(prefix="halite-model-unit-")
        self.addCleanup(directory.cleanup)
        self.path=Path(directory.name)

    def test_complete_run_has_exact_denominators_and_never_selects_a_model(self):
        tmp_path=self.path
        provider=SyntheticProvider();out=tmp_path/'run'
        result=mc.run(packet(tmp_path),['synthetic-a','synthetic-b'],out,client=provider)
        assert result['complete'] and result['n_attempts']==60 and result['n_responses']==60
        assert result['provider_errors']==0 and result['selected_model'] is None
        assert len(provider.calls)==62  # two excluded warmups
        assert len(mc.read_rows(out/'warmups.jsonl'))==2
        assert all(row['valid_output_share']==1 for row in result['summaries'])
        assert all(row['unsupported_rate'] is None for row in result['summaries'])
        prose=[r for r in result['summaries'] if r['task']=='prose' and r['arm']=='evidence']
        assert all(r['in_evidence_citation_share']==1 and r['unrated_sentences']==10 for r in prose)
        manifest=json.loads((out/'manifest.json').read_text())
        assert manifest['plan']['execution_source']=='injected_test_client'
        assert manifest['plan']['server_hardware_verified'] is False
        assert 'No model has been selected' in (out/'COMPARISON.md').read_text()
        with self.assertRaises(FileExistsError):mc.run(packet_path:=tmp_path/'synthetic-packet.json',['synthetic-a','synthetic-b'],out,client=provider)
        count=len(provider.calls)
        mc.run(packet_path,['synthetic-a','synthetic-b'],out,resume=True,client=provider)
        assert len(provider.calls)==count

    def test_resume_preserves_prior_attempts_rewarms_pending_model_and_detects_tampering(self):
        tmp_path=self.path
        source=packet(tmp_path);provider=SyntheticProvider();provider.interrupt_at=7;out=tmp_path/'run'
        with self.assertRaises(KeyboardInterrupt):mc.run(source,['synthetic-a'],out,client=provider)
        before=(out/'responses.jsonl').read_bytes();assert len(mc.read_rows(out/'responses.jsonl'))==5
        provider.interrupt_at=None
        result=mc.run(source,['synthetic-a'],out,resume=True,client=provider)
        assert result['n_attempts']==30 and (out/'responses.jsonl').read_bytes().startswith(before)
        assert len(mc.read_rows(out/'warmups.jsonl'))==2
        rows=mc.read_rows(out/'responses.jsonl');rows[0]['assessment']['valid_output']=False
        (out/'responses.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with self.assertRaisesRegex(ValueError,'assessment'):mc.run(source,['synthetic-a'],out,resume=True,client=provider)

    def test_resume_refuses_changed_model_and_partial_journal_without_discarding_bytes(self):
        tmp_path=self.path
        source=packet(tmp_path);provider=SyntheticProvider();out=tmp_path/'run'
        mc.run(source,['synthetic-a'],out,client=provider)
        provider.digest='different-model'
        with self.assertRaisesRegex(ValueError,'changed'):mc.run(source,['synthetic-a'],out,resume=True,client=provider)
        provider.digest='synthetic-not-a-model'
        journal=out/'responses.jsonl';journal.write_bytes(journal.read_bytes()+b'{"partial":')
        raw=journal.read_bytes()
        with self.assertRaisesRegex(ValueError,'Incomplete journal'):mc.run(source,['synthetic-a'],out,resume=True,client=provider)
        assert journal.read_bytes()==raw

    def test_provider_failure_stays_in_denominator_and_no_auto_retry(self):
        tmp_path=self.path
        source=packet(tmp_path);provider=SyntheticProvider();provider.error_at=2
        result=mc.run(source,['synthetic-a'],tmp_path/'run',client=provider)
        assert result['provider_errors']==1 and result['n_attempts']==30 and result['n_responses']==29
        assert len(provider.calls)==31
        assert any(r['valid_output_share']<1 for r in result['summaries'])
        assert mc.read_rows(tmp_path/'run/responses.jsonl')[0]['error']=='TimeoutError'

    def test_real_m4_role_cannot_be_fabricated_by_linux_or_remote_endpoint(self):
        tmp_path=self.path
        source=packet(tmp_path)
        patcher=patch.object(mc,'hardware',new=lambda:{'system':'Linux','machine':'x86_64'});self.addCleanup(patcher.stop);patcher.start()
        with self.assertRaisesRegex(ValueError,'Apple M4'):mc.run(source,['synthetic-a','synthetic-b'],tmp_path/'run',client=SyntheticProvider(),role='m4_comparison')
        patcher=patch.object(mc,'hardware',new=lambda:{'system':'Darwin','machine':'arm64','chip':'Apple M4','memory_bytes':16*1024**3});self.addCleanup(patcher.stop);patcher.start()
        remote=SyntheticProvider();remote.local=False
        with self.assertRaisesRegex(ValueError,'loopback'):mc.run(source,['synthetic-a','synthetic-b'],tmp_path/'run',client=remote,role='m4_comparison')

    def test_schema_negation_ids_and_no_evidence_are_audited_without_fake_support(self):
        tmp_path=self.path
        case=mc.load_packet(packet(tmp_path))['cases'][1]
        prompt=messages(case,baseline=True)
        assert json.loads(prompt[-1]['content'].split('\n')[-1])['evidence']==[]
        assert 'no smoke' in prompt[-1]['content']
        raw={'done':True,'message':{'content':'Pump leaked [REC2024000001].'}}
        evidence=mc.assess(raw,case);baseline=mc.assess(raw,case,baseline=True)
        assert evidence['in_evidence_citation_occurrences']==1
        assert baseline['in_evidence_citation_occurrences']==0 and baseline['grounding']['unsupported_count']==1
        assert baseline['unsupported_rate'] is None
        for content in [None,{},'']:
            result=mc.assess({'done':True,'message':{'content':content}},case)
            assert result['valid_output'] is False
        assert mc.assess({'done':True,'done_reason':'length','message':{'content':'Pump leaked.'}},case)['valid_output'] is False
        facts=copy.deepcopy(case);facts['task']='facts'
        assert mc.assess({'done':True,'message':{'content':'```json\n{}\n```'}},facts)['valid_output'] is False

    def test_packet_tampering_and_selected_checker_without_references_are_rejected(self):
        tmp_path=self.path
        source=packet(tmp_path);data=json.loads(source.read_text());data['cases'][0]['observation']='Changed'
        source.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'fingerprint'):mc.load_packet(source)
        settings=tmp_path/'checker.json';settings.write_text(json.dumps({'status':'selected'}))
        with self.assertRaisesRegex(ValueError,'human-label'):mc.load_parameters(settings)
        for url in ['http://remote.example:11434','https://user:secret@example.com','https://example.com?token=secret']:
            with self.assertRaises(ValueError):mc.Ollama(url)

    def test_portable_zip_is_reproducible_and_runs_with_no_site_packages(self):
        tmp_path=self.path
        source=packet(tmp_path);readme=tmp_path/'README.md';readme.write_text('Synthetic bundle test only.\n')
        _,first=bundle(source,tmp_path/'first.zip',readme)
        _,second=bundle(source,tmp_path/'second.zip',readme)
        assert first==second
        target=tmp_path/'extracted'
        with zipfile.ZipFile(tmp_path/'first.zip') as archive:archive.extractall(target)
        result=subprocess.run([sys.executable,'-I','-S',str(target/'run_compare.py'),'--help'],capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        assert '--models' in result.stdout
        rejected=subprocess.run([sys.executable,'-I','-S',str(target/'run_compare.py'),'--packet=foreign.json'],capture_output=True,text=True)
        assert rejected.returncode!=0 and 'do not replace' in rejected.stderr
        (target/'investigation/grounding.py').write_text('tampered source')
        changed=subprocess.run([sys.executable,'-I','-S',str(target/'run_compare.py'),'--help'],capture_output=True,text=True)
        assert changed.returncode!=0 and 'differs from its manifest' in changed.stderr


    def test_native_transport_rejects_unknown_models_and_oversized_prompts_before_chat(self):
        transport=mc.Ollama('http://127.0.0.1:9')
        transport.request=lambda *args: {'models':[{'name':'other-model','digest':'synthetic'}]}
        with self.assertRaisesRegex(ValueError,'Exact installed'):
            transport.identity('requested-model')
        with self.assertRaisesRegex(ValueError,'context budget'):
            transport.chat('requested-model',[{'role':'user','content':'x'*3201}])
        with self.assertRaisesRegex(ValueError,'timeout'):
            mc.Ollama('http://127.0.0.1:9',timeout=float('inf'))

    def test_raw_wrong_model_response_is_retained_as_a_failure(self):
        tmp_path=self.path
        class WrongModel(SyntheticProvider):
            def chat(self,model,prompt,**kwargs):
                raw=super().chat(model,prompt,**kwargs)
                if not prompt[0]['content'].startswith('Reply with'):
                    raw['model']='wrong-model'
                return raw
        result=mc.run(packet(tmp_path),['synthetic-a'],tmp_path/'run',client=WrongModel())
        assert result['provider_errors']==30 and result['n_responses']==0
        assert all(row['raw']['model']=='wrong-model' for row in mc.read_rows(tmp_path/'run/responses.jsonl'))


    def test_m4_candidates_require_actual_parameter_metadata(self):
        tmp_path=self.path
        source=packet(tmp_path)
        with patch.object(mc,'hardware',return_value={'system':'Darwin','machine':'arm64','chip':'Apple M4','memory_bytes':16*1024**3}):
            with self.assertRaisesRegex(ValueError,'7–8B'):
                mc.run(source,['synthetic-a','synthetic-b'],tmp_path/'run',client=SyntheticProvider(),role='m4_comparison')


if __name__=="__main__":
    unittest.main()
