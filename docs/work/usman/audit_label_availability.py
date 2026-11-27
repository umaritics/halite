"""Reproduce the pre-test timing audit from only the frozen 2023/2024 projections."""
import argparse
from collections import Counter
import csv
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'backend'))
from investigation.experiments.download_projection import COLUMNS


def audit(data_directory):
    base = REPO/'backend/investigation/experiments/results/decision_selection_2024_v2'
    selection = json.loads((base/'selection.json').read_text())
    expected = {s['file']:s['projection_sha256'] for s in selection['selection_corpus']['sources']}
    result = {'purpose':'Pre-held-out label-availability audit; no 2025 archive read.', 'splits':{}}
    for year, kind in ((2023,'fit'),(2024,'selection')):
        cases = json.loads((base/(kind+'_cases.json')).read_text())
        wanted = {c['answer_id'] for c in cases}
        source = Path(data_directory)/f'usman_decision_{year}.csv.gz'
        metadata = json.loads(source.with_suffix(source.suffix+'.json').read_text())
        found, digest = {}, hashlib.sha256()
        with gzip.open(source,'rt',encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream):
                digest.update((json.dumps({key:row[key] for key in COLUMNS},ensure_ascii=False,separators=(',',':'))+'\n').encode())
                rid = row['OperatorControlNumber'].strip().upper()
                if rid in wanted:found[rid] = row['SubmissionDate']
        if digest.hexdigest() != expected[source.name] or digest.hexdigest() != metadata['projection_sha256']:
            raise ValueError('Timing audit requires the exact frozen source projection.')
        if wanted != found.keys():
            raise ValueError('A selected outcome report is missing from its original source.')
        result['splits'][kind] = {
            'n_case_pairs':len(cases), 'n_unique_answer_reports':len(wanted),
            'answer_submission_years':dict(sorted(Counter(datetime.fromisoformat(v).year for v in found.values()).items())),
            'latest_answer_submission':max(found.values(),key=datetime.fromisoformat),
            'source_projection_metadata':metadata, 'missing_answer_reports':0,
            'source_projection_fingerprint_verified':True}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-directory',default=str(REPO/'backend/data/raw'))
    args = parser.parse_args()
    print(json.dumps(audit(args.data_directory),indent=2))
