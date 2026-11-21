"""Build a blinded 150-pair human review packet from frozen 2023/2024 FAA text."""
import argparse
from collections import defaultdict
import csv
import hashlib
import html
import json
from pathlib import Path
import random

from investigation.experiments.offline import Corpus, load_records, UNKNOWN
from investigation.grounding import split_sentences


def make_pairs(corpus,query_ids,*,seed=1729,groups=50):
    parts=defaultdict(list)
    for r in corpus.sorted_records:
        if r['year'] in (2023,2024):parts[r['part_name']].append(r)
    ids=sorted(set(query_ids));random.Random(seed).shuffle(ids)
    result=[];origins=[];used_reports=set()
    reserved_queries=set(ids)
    for rid in ids:
        query=corpus.records[rid]
        if query['year']!=2024 or query['part_name'] in UNKNOWN:continue
        sentences=[s for s in split_sentences(query['text']) if 30<=len(s)<=600 and 'SUPPLEMENTAL' not in s.upper()]
        if not sentences:continue
        sentence=sentences[0]
        visible=lambda r:r['submitted_at']<query['submitted_at'] and corpus.chains[r['record_id']]!=corpus.chains[rid]
        same=next((r for r in parts[query['part_name']] if visible(r) and sentence not in r['text'] and r['record_id'] not in used_reports|reserved_queries),None)
        other=next((r for r in corpus.sorted_records if r['year'] in (2023,2024) and r['part_name'] not in UNKNOWN|{query['part_name']}
                    and r['jasc_code']==query['jasc_code'] and visible(r) and r['record_id'] not in used_reports|reserved_queries),None)
        if same is None or other is None:continue
        origins.append(rid)
        used_reports.update((same['record_id'],other['record_id']))
        for arm,report in [('same_source',query),('same_part_other_report',same),('same_jasc_other_part',other)]:
            pairid=hashlib.sha256(f'{rid}:{arm}:{report["record_id"]}:{sentence}:{seed}'.encode()).hexdigest()[:16]
            result.append({'pair_id':pairid,'original_id':rid,'year':2024,'sentence':sentence+' ['+report['record_id']+']',
                           'report':{key:report[key] for key in ('record_id','text','part_name')},
                           'sampling_arm':arm,'claim_source_record_id':rid})
        if len(origins)==groups:break
    if len(origins)!=groups:raise ValueError('Insufficient eligible original groups for the declared packet size.')
    random.Random(seed+1).shuffle(result)
    # Every original and reused reference stays within one partition. Shared
    # reference reports connect groups; splitting a component would leak text.
    connected={rid:{rid} for rid in origins}
    refs=defaultdict(set)
    for p in result:refs[p['report']['record_id']].add(p['original_id'])
    for linked in refs.values():
        merged=set().union(*(connected[rid] for rid in linked))
        for rid in merged:connected[rid]=merged
    components={tuple(sorted(c)) for c in connected.values()}
    components=sorted(components,key=lambda c:(-len(c),c))
    fit,validation=set(),set()
    for component in components:
        target=fit if len(fit)<round(groups*2/3) else validation
        target.update(component)
    if not fit or not validation:raise ValueError('Reference sharing prevents an independent split; change packet construction.')
    return result,sorted(fit),sorted(validation)


def review_fingerprint(pairs):
    view=[{key:p[key] for key in ('pair_id','sentence','report')} for p in pairs]
    return hashlib.sha256(json.dumps(view,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def review_html(pairs,reviewer=""):
    # The view receives no sampling arm, model score, split or expected label.
    view=[{key:p[key] for key in ('pair_id','sentence','report')} for p in pairs]
    data=json.dumps(view,ensure_ascii=False).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Halite independent sentence review</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#17212b;background:#f4f6f8}article{background:white;border:1px solid #ccd3db;border-radius:10px;padding:1rem;margin:1rem 0}textarea,input,select,button{font:inherit;padding:.6rem;max-width:100%;box-sizing:border-box}textarea{width:100%;min-height:90px}button{cursor:pointer}#report{white-space:pre-wrap;overflow-wrap:anywhere}label{display:block;margin:.5rem 0}nav{display:flex;gap:.5rem;flex-wrap:wrap}</style>
<h1>Independent sentence review</h1><p>Read only the supplied report. Label whether it supports the claim: supported, partly supported, or unsupported. Assess negation, named parts and quantities. Do not use outside aircraft knowledge. Do not infer a cause or approve a repair. Work independently without consulting the other reviewer or any checker prediction.</p>
<p>This is a constructed calibration sample from real FAA text, not measured model answers. Sampling category and checker scores are hidden. Labels begin empty; nothing is auto-labelled.</p>
<label>Your reviewer identity <input id="reviewer" value="REVIEWER_VALUE" autocomplete="name" required></label>
<p id="progress" role="status"></p><article><h2>Claim</h2><p id="claim"></p><h2>Cited report</h2><p id="record"></p><p id="report"></p>
<label>Label <select id="label"><option value="">Choose a label</option><option value="supported">Supported</option><option value="partly_supported">Partly supported</option><option value="unsupported">Unsupported</option></select></label>
<label>Your rationale <textarea id="rationale" placeholder="Explain the supporting text or the mismatch; do not copy another reviewer."></textarea></label></article>
<nav><button id="previous">Previous</button><button id="save">Save label and next</button><button id="export">Export completed CSV</button><button id="draft">Export draft JSON</button><label>Resume your own draft <input id="import" type="file" accept="application/json"></label></nav>
<p id="error" role="alert"></p><p>Nothing is sent to a server or saved automatically. Export a draft before closing. Send completed independent CSVs for agreement and adjudication; do not merge them yourself.</p>
<script>const pairs=DATA; const packetFingerprint='PACKET_FINGERPRINT'; let index=0; const answers={}; const el=id=>document.getElementById(id); function show(){const p=pairs[index];el('claim').textContent=p.sentence;el('record').textContent=p.report.record_id+' · '+p.report.part_name;el('report').textContent=p.report.text;el('label').value=answers[p.pair_id]?.label||'';el('rationale').value=answers[p.pair_id]?.rationale||'';el('progress').textContent=`Pair ${index+1} of ${pairs.length} · ${Object.keys(answers).length} saved`;el('previous').disabled=index===0;el('error').textContent='';} function save(){const name=el('reviewer').value.trim(),label=el('label').value,rationale=el('rationale').value.trim();if(!name||!label||!rationale){el('error').textContent='Reviewer, label and rationale are all required.';return false;}if(Object.values(answers).some(a=>a.reviewer!==name)){el('error').textContent='Use the same reviewer identity for every label in your independent file.';return false;}answers[pairs[index].pair_id]={pair_id:pairs[index].pair_id,label,reviewer:name,reviewed_at:new Date().toISOString(),rationale,packet_sha256:packetFingerprint};return true;} function download(name,data,type){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([data],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);} el('save').onclick=()=>{if(save()){index=Math.min(index+1,pairs.length-1);show();}};el('previous').onclick=()=>{index=Math.max(0,index-1);show();};el('draft').onclick=()=>download('halite-review-draft.json',JSON.stringify({reviewer:el('reviewer').value,answers,index,current:{label:el('label').value,rationale:el('rationale').value},packet_sha256:packetFingerprint},null,2),'application/json');el('export').onclick=()=>{if(!save())return;if(Object.keys(answers).length!==pairs.length){el('error').textContent='Complete every pair before exporting the label CSV. Use draft export to resume later.';return;}const keys=['pair_id','label','reviewer','reviewed_at','rationale','packet_sha256'];const quote=value=>{const s=String(value??'');return '"'+s.replaceAll('"','""')+'"';};download('halite-independent-labels.csv',[keys,...pairs.map(p=>keys.map(k=>answers[p.pair_id][k]))].map(row=>row.map(quote).join(',')).join('\\n')+'\\n','text/csv');};el('import').onchange=async event=>{try{const d=JSON.parse(await event.target.files[0].text());if(d.packet_sha256!==packetFingerprint)throw Error('This draft belongs to a different packet.');for(const [id,a] of Object.entries(d.answers||{})){if(!pairs.some(p=>p.pair_id===id)||!['supported','partly_supported','unsupported'].includes(a.label)||!a.reviewer||!a.reviewed_at||!a.rationale||a.pair_id!==id||a.packet_sha256!==packetFingerprint||a.reviewer!==d.reviewer.trim())throw Error('Invalid or foreign draft.');}Object.keys(answers).forEach(k=>delete answers[k]);Object.assign(answers,d.answers);el('reviewer').value=d.reviewer||'';index=Number.isInteger(d.index)&&d.index>=0&&d.index<pairs.length?d.index:0;show();if(d.current){el('label').value=d.current.label||'';el('rationale').value=d.current.rationale||'';}}catch(error){el('error').textContent=error.message;}};show();</script></html>'''.replace('REVIEWER_VALUE',html.escape(reviewer,quote=True)).replace('PACKET_FINGERPRINT',review_fingerprint(pairs)).replace('DATA',data)


def build(sources,baseline,output):
    output=Path(output)
    if output.exists():raise FileExistsError('Preserve prior packet; use a fresh directory.')
    records,meta=load_records(sources)
    selection=json.loads((Path(baseline)/'selection.json').read_text())
    if meta['corpus_sha256']!=selection['selection_corpus']['corpus_sha256'] or any(r['year'] not in (2023,2024) for r in records.values()):
        raise ValueError('Exact frozen 2023/2024 sources only; no 2025 permitted.')
    cases=json.loads((Path(baseline)/'selection_cases.json').read_text())
    pairs,fit,validation=make_pairs(Corpus(records),[c['query_id'] for c in cases])
    output.mkdir(parents=True)
    packet={'method':'constructed-sentence-pairs-v1','source_kind':'Real FAA text; constructed pairing, not model output or human labels',
            'corpus':meta,'review_sha256':review_fingerprint(pairs),'seed':1729,'pairs':pairs,'fit_originals':fit,'validation_originals':validation,'held_out_2025_used':False}
    method_files=[Path(__file__),Path(__file__).with_name('offline.py'),Path(__file__).parent.parent/'grounding.py']
    packet['method_files_sha256']={str(p.relative_to(Path(__file__).parents[2])):hashlib.sha256(p.read_bytes()).hexdigest() for p in method_files}
    packet['intended_reviewers']=['Muhammad Usman Al Haq','Muhammad Umar']
    (output/'packet.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n')
    (output/'review.html').write_text(review_html(pairs))
    (output/'review_usman.html').write_text(review_html(pairs,'Muhammad Usman Al Haq'))
    (output/'review_umar.html').write_text(review_html(pairs,'Muhammad Umar'))
    for reviewer in ('first','second'):
        with (output/(reviewer+'_labels_TEMPLATE.csv')).open('w',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['pair_id','label','reviewer','reviewed_at','rationale','packet_sha256'])
            writer.writerows([p['pair_id'],'','','','',packet['review_sha256']] for p in pairs)
    return packet


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',nargs='+',required=True);parser.add_argument('--baseline',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();result=build(**vars(args));print(json.dumps({'pairs':len(result['pairs']),'fit_originals':len(result['fit_originals']),'validation_originals':len(result['validation_originals'])}))
