"""Independent human-label import, agreement and held-separate threshold selection."""
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path

from investigation.grounding import GroundingParameters, check_reply

LABELS=('supported','partly_supported','unsupported')


def load_labels(path, *, expected_ids, packet_sha256=None):
    """No automatic fill, duplicate suppression or invented agreement."""
    rows={}
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        required={'pair_id','label','reviewer','reviewed_at','rationale'}
        if packet_sha256 is not None:required.add('packet_sha256')
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or not required <= set(reader.fieldnames):
            raise ValueError('Label file requires pair_id, label, reviewer, reviewed_at and rationale.')
        for row in reader:
            if None in row or any(row.get(key) is None for key in required):
                raise ValueError('Malformed label row.')
            rid=row['pair_id'].strip()
            if rid not in expected_ids or rid in rows:
                raise ValueError('Unexpected or duplicate labelled pair.')
            if row['label'] not in LABELS or not row['reviewer'].strip() or not row['reviewed_at'].strip() or not row['rationale'].strip():
                raise ValueError('Every label needs an actual reviewer, review time and rationale.')
            try:
                if datetime.fromisoformat(row['reviewed_at'].replace('Z','+00:00')).utcoffset() is None:
                    raise ValueError('Naive timestamp.')
            except ValueError as exc:
                raise ValueError('Review time must be an explicit ISO timestamp with timezone.') from exc
            if packet_sha256 is not None and row['packet_sha256']!=packet_sha256:
                raise ValueError('Labels belong to a different review packet.')
            rows[rid]=row
    if set(rows)!=set(expected_ids):
        raise ValueError('Incomplete label file; missing pairs cannot be silently excluded.')
    return rows


def agreement(first,second):
    if not first or set(first)!=set(second):
        raise ValueError('Agreement needs the same nonempty pair IDs from both reviewers.')
    reviewers=[{' '.join(r['reviewer'].casefold().split()) for r in rows.values()} for rows in (first,second)]
    if any(len(names)!=1 for names in reviewers) or reviewers[0] & reviewers[1]:
        raise ValueError('Two distinct, consistently identified independent reviewers are required.')
    n=len(first)
    matches=sum(first[rid]['label']==second[rid]['label'] for rid in first)
    a=Counter(r['label'] for r in first.values());b=Counter(r['label'] for r in second.values())
    observed=matches/n
    expected=sum(a[label]*b[label] for label in LABELS)/n**2
    kappa=(observed-expected)/(1-expected) if expected<1 else None
    disagreements=[rid for rid in first if first[rid]['label']!=second[rid]['label']]
    return {'n':n,'observed_agreement':observed,'expected_agreement':expected,'cohens_kappa':kappa,
            'disagreement_ids':sorted(disagreements),'reviewers':[next(iter(names)) for names in reviewers],
            'kappa_note':'Undefined when expected agreement is one; never fabricated as perfect.' if kappa is None else None}


def consensus(first,second,adjudicated=None):
    summary=agreement(first,second)
    if adjudicated is not None and set(adjudicated)!=set(summary['disagreement_ids']):
        raise ValueError('Adjudication IDs must match exactly the disagreement set.')
    result={}
    for rid in first:
        a,b=first[rid]['label'],second[rid]['label']
        if a==b:
            result[rid]=a
        else:
            decision=(adjudicated or {}).get(rid)
            if not decision or decision.get('label') not in LABELS or not decision.get('reviewer') or not decision.get('rationale'):
                raise ValueError('Every disagreement requires explicit human adjudication.')
            result[rid]=decision['label']
    return result,summary


def metrics(predictions,labels):
    if set(predictions)!=set(labels) or not labels:
        raise ValueError('Metrics need identical nonempty case IDs.')
    expected={'supported':'supported','partly_supported':'weak','unsupported':'unsupported'}
    matrix={truth:dict.fromkeys(('supported','weak','unsupported','uncited','unrated'),0) for truth in LABELS}
    for rid,truth in labels.items():
        matrix[truth][predictions[rid]]+=1
    binary={}
    for positive,truth in [('supported','supported'),('unsupported','unsupported')]:
        tp=matrix[truth][positive]
        fp=sum(row[positive] for key,row in matrix.items() if key!=truth)
        fn=sum(value for key,value in matrix[truth].items() if key!=positive)
        precision=tp/(tp+fp) if tp+fp else None
        recall=tp/(tp+fn) if tp+fn else None
        f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
        binary[positive]={'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':f1}
    return {'n':len(labels),'accuracy':sum(predictions[rid]==expected[truth] for rid,truth in labels.items())/len(labels),
            'confusion':matrix,'classes':binary}


def select_thresholds(pairs,labels,*,fit_originals,validation_originals):
    """No overlap by original report; no held-out 2025 or whitelist selection by proxy."""
    if set(fit_originals)&set(validation_originals) or not fit_originals or not validation_originals:
        raise ValueError('Fit and validation original IDs must be nonempty and disjoint.')
    by_id={p['pair_id']:p for p in pairs}
    if len(by_id)!=len(pairs) or set(by_id)!=set(labels) or any(p['year'] not in (2023,2024) for p in pairs):
        raise ValueError('Threshold selection requires all labelled 2023/2024 pairs only.')
    fit=[p for p in pairs if p['original_id'] in fit_originals]
    validation=[p for p in pairs if p['original_id'] in validation_originals]
    fit_refs={p['report']['record_id'] for p in fit};validation_refs={p['report']['record_id'] for p in validation}
    if fit_refs & validation_refs:
        raise ValueError('Reference report IDs overlap the threshold fit and validation sets.')
    if not fit or not validation or len(fit)+len(validation)!=len(pairs):
        raise ValueError('Every pair must belong to the declared split.')
    # The current real adapter is absent: select lexical thresholds only. Never
    # mix dense synthetic-test vectors into a real calibration result.
    scores={}
    for p in pairs:
        checked=check_reply(p['sentence'],[p['report']])['sentences']
        if len(checked)!=1:raise ValueError('Every review pair must contain exactly one claim sentence.')
        scores[p['pair_id']]=checked[0]
    def predictions(rows,lo,hi):
        result={}
        for p in rows:
            item=scores[p['pair_id']]
            score=item['score']
            if item['invalid_citations'] or score is None or score<lo:level='unsupported'
            elif score>=hi and any(c['eligible_for_supported'] and c['score']==score for c in item['candidates']):level='supported'
            else:level='weak'
            if not item['citations']:level='uncited'
            result[p['pair_id']]=level
        return result
    table=[]
    for lo in (.1,.2,.3,.4,.5,.6,.7):
        for hi in (.5,.6,.7,.8,.9,1.0):
            if lo>=hi:continue
            pred=predictions(fit,lo,hi)
            measured=metrics(pred,{p['pair_id']:labels[p['pair_id']] for p in fit})
            # Fit-only macro F1. Selection on fit, a separate validation readout.
            per_class=[]
            for truth,predicted in [('supported','supported'),('partly_supported','weak'),('unsupported','unsupported')]:
                tp=measured['confusion'][truth][predicted]
                fp=sum(row[predicted] for key,row in measured['confusion'].items() if key!=truth)
                fn=sum(v for key,v in measured['confusion'][truth].items() if key!=predicted)
                per_class.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
            table.append({'theta_lo':lo,'theta_hi':hi,'macro_f1':sum(per_class)/3,'fit_metrics':measured})
    chosen=max(table,key=lambda row:(row['macro_f1'],row['theta_hi'],row['theta_lo']))
    validation_metrics=metrics(predictions(validation,chosen['theta_lo'],chosen['theta_hi']),{p['pair_id']:labels[p['pair_id']] for p in validation})
    params=GroundingParameters(chosen['theta_lo'],chosen['theta_hi'],1,provenance='Human-label fit proposal; user acceptance still required.')
    return {'proposal':{**vars(params),'whitelist':list(params.whitelist)},'fit_n':len(fit),'validation_n':len(validation),'fit_originals':sorted(fit_originals),
            'validation_originals':sorted(validation_originals),'fit_choice':chosen,'validation_metrics':validation_metrics,
            'fit_table':table,'held_out_2025_used':False,'accepted':False}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate_files(packet,first,second,*,output,adjudications=None):
    data=json.loads(Path(packet).read_text())
    pairs=data['pairs']
    ids={p['pair_id'] for p in pairs}
    if len(ids)!=len(pairs):raise ValueError('Duplicate packet pair IDs.')
    from investigation.experiments.grounding_packet import review_fingerprint
    digest=review_fingerprint(pairs)
    if data.get('review_sha256')!=digest:raise ValueError('Packet fingerprint mismatch.')
    a=load_labels(first,expected_ids=ids,packet_sha256=digest);b=load_labels(second,expected_ids=ids,packet_sha256=digest)
    adjudicated=json.loads(Path(adjudications).read_text()) if adjudications else None
    labels,agreed=consensus(a,b,adjudicated)
    result=select_thresholds(pairs,labels,fit_originals=data['fit_originals'],validation_originals=data['validation_originals'])
    result.update(agreement=agreed,sources_sha256={'packet':sha(packet),'first_labels':sha(first),'second_labels':sha(second),
                  'adjudications':sha(adjudications) if adjudications else None})
    method_files=[Path(__file__),Path(__file__).with_name('grounding_packet.py'),Path(__file__).parent.parent/'grounding.py']
    result['method_files_sha256']={str(p.relative_to(Path(__file__).parents[2])):sha(p) for p in method_files}
    out=Path(output)
    if out.exists():raise FileExistsError('Preserve prior evaluation; use a fresh output path.')
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('packet','first','second','output'):parser.add_argument('--'+key,required=True)
    parser.add_argument('--adjudications')
    args=parser.parse_args()
    evaluate_files(**vars(args))
