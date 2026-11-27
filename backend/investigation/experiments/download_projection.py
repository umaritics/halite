"""Stream FAA sources into an isolated research projection, not V1's corpus builder."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.request

COLUMNS = ('OperatorControlNumber', 'DifficultyDate', 'SubmissionDate', 'RegistryNNumber',
           'AircraftMake', 'AircraftModel', 'PartName', 'PartCondition', 'PartLocation', 'JASCCode',
           'Discrepancy', 'NatureOfConditionA', 'PrecautionaryProcedureA', 'StageOfOperationCode', 'HowDiscoveredCode')


def download(year, destination):
    if year not in (2023, 2024):
        raise ValueError('Preparation deliberately does not download held-out 2025.')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError('Refusing to overwrite a source projection.')
    temporary = destination.with_suffix(destination.suffix + '.partial')
    digest = hashlib.sha256()
    url = f'https://external.apic4e.faa.gov/sdrs/retrieve/SDR-{year}.csv'
    count = 0
    try:
        with urllib.request.urlopen(url, timeout=120) as response, io.TextIOWrapper(response, encoding='utf-8-sig', newline='') as source, gzip.open(temporary, 'wt', encoding='utf-8', newline='') as output:
            reader = csv.DictReader(source)
            if not set(COLUMNS).issubset(reader.fieldnames or []):
                raise ValueError('FAA response is missing required columns.')
            writer = csv.DictWriter(output, fieldnames=COLUMNS)
            writer.writeheader()
            for record in reader:
                projected = {key: record[key] for key in COLUMNS}
                digest.update((json.dumps(projected, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
                writer.writerow(projected)
                count += 1
        if not count:
            raise ValueError('Empty FAA response.')
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    meta = {'source': url, 'year': year, 'n_rows': count, 'columns': list(COLUMNS),
            'projection_sha256': digest.hexdigest(), 'fingerprint_definition': 'Canonical ordered projected-row JSON UTF-8, newline per row.'}
    destination.with_suffix(destination.suffix + '.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(download(args.year, args.output), indent=2))
