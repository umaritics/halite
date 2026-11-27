"""Audit the checked-in unlabelled packet without assigning any human labels."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'))
from investigation.grounding import check_reply,split_sentences
from investigation.experiments.grounding_packet import review_fingerprint

folder=ROOT/'docs/work/usman/grounding_review_v1'
data=json.loads((folder/'packet.json').read_text())
pairs=data['pairs']
assert len(pairs)==150 and len({p['pair_id'] for p in pairs})==150
assert data['review_sha256']==review_fingerprint(pairs)
assert data['held_out_2025_used'] is False
assert {p['year'] for p in pairs}=={2024}
fit=set(data['fit_originals']);validation=set(data['validation_originals'])
assert len(fit)==33 and len(validation)==17 and not fit&validation
refs=[{p['report']['record_id'] for p in pairs if p['original_id'] in ids} for ids in (fit,validation)]
assert not refs[0]&refs[1]
for p in pairs:
    assert len(split_sentences(p['sentence']))==1
    checked=check_reply(p['sentence'],[p['report']])['sentences'][0]
    assert checked['valid_citations']==[p['report']['record_id']]
    assert checked['level']=='unrated'
for name in ('first','second'):
    rows=list(csv.DictReader((folder/(name+'_labels_TEMPLATE.csv')).open()))
    assert len(rows)==150
    assert all(not row['label'] and not row['reviewer'] and not row['rationale'] and not row['reviewed_at'] for row in rows)
    assert all(row['packet_sha256']==data['review_sha256'] for row in rows)
for name,digest in data['method_files_sha256'].items():
    assert hashlib.sha256((ROOT/'backend'/name).read_bytes()).hexdigest()==digest,name
for name in ('review_usman.html','review_umar.html'):
    page=(folder/name).read_text()
    assert 'sampling_arm' not in page and 'checker_score' not in page
print(json.dumps({'pairs':150,'fit_pairs':99,'validation_pairs':51,'reference_overlap':0,'blank_templates':True,
                  'single_sentence_and_exact_citation_checks':True,'method_hashes_match':True,'held_out_2025_used':False,
                  'human_labels_supplied':False,'review_sha256':data['review_sha256']},indent=2))
