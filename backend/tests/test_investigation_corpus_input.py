import csv
import gzip
import json

import pytest

from investigation.experiments.download_projection import COLUMNS, download
from investigation.experiments.offline import load_records


def row(rid='SOURCE01', **changes):
    result = dict.fromkeys(COLUMNS, '')
    result.update(OperatorControlNumber=rid, DifficultyDate='01/01/2023', SubmissionDate='2023-01-02T10:00:00Z',
                  RegistryNNumber='N-1', PartName='PUMP', Discrepancy='Pressure loss')
    result.update(changes)
    return result


def write(path, rows):
    with gzip.open(path, 'wt', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_projection_dedup_ambiguous_ids_bad_dates_and_fingerprints(tmp_path):
    path = tmp_path / 'source.csv.gz'
    write(path, [row(), row(), row('AMBIG001'), row('AMBIG001', PartName='SENSOR'), row('BADDATE1', SubmissionDate='unknown')])
    records, meta = load_records([path])
    assert list(records) == ['SOURCE01']
    assert meta['duplicate_identical'] == 1 and meta['ambiguous_ids'] == 1 and meta['invalid'] == 1
    assert records['SOURCE01']['submitted_at'].utcoffset().total_seconds() == 0
    path.with_suffix('.gz.json').write_text(json.dumps({'projection_sha256': 'wrong'}))
    with pytest.raises(ValueError, match='fingerprint'):
        load_records([path])


def test_preparation_download_refuses_held_out_and_overwrites_before_network(tmp_path):
    with pytest.raises(ValueError, match='held-out'):
        download(2025, tmp_path / 'heldout.gz')
    existing = tmp_path / 'existing.gz'
    existing.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        download(2023, existing)
    assert existing.read_bytes() == b'keep'
