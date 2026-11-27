"""Freeze a part-name guard vocabulary from the fit year, never from held-out data."""
import argparse
import hashlib
import json
from pathlib import Path

from investigation.experiments.offline import load_records, UNKNOWN


def fit(source,output):
    records,meta=load_records([source])
    if not records or any(r['year']!=2023 for r in records.values()):
        raise ValueError('Grounding part vocabulary requires only 2023 records.')
    names=sorted({r['part_name'] for r in records.values()}-UNKNOWN)
    payload={'version':'grounding-parts-v1','fit_years':[2023],'corpus':meta,'parts':names}
    payload['parts_sha256']=hashlib.sha256(json.dumps(names,separators=(',',':')).encode()).hexdigest()
    path=Path(output)
    if path.exists():raise FileExistsError('Preserve a fitted vocabulary; use a fresh path.')
    path.write_text(json.dumps(payload,indent=2)+'\n')
    return payload


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();result=fit(args.source,args.output);print(json.dumps({'parts':len(result['parts']),'fit_years':result['fit_years'],'corpus_sha256':result['corpus']['corpus_sha256']}))
