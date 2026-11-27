"""Artifact provenance and fit-year boundaries; no invented research labels."""
import csv
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
import zipfile

import pytest

from investigation.experiments.download_projection import COLUMNS
from investigation.experiments.fit_grounding_vocabulary import fit
from investigation.experiments.import_faa_codes import TABLES, extract, workbook_cells

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'docs/work/usman/evidence/phase5-faa-lookup-tables.zip'
CODEBOOK = ROOT / 'backend/investigation/data/faa_codes.json'


def test_retained_official_faa_archive_reproduces_every_committed_code_and_fingerprint():
    expected = json.loads(CODEBOOK.read_text())
    actual = extract(ARCHIVE, retrieved_at_utc=expected['retrieved_at_utc'])
    assert actual == expected
    assert set(actual['attributes']) == set(TABLES)
    assert all(table['values'] for table in actual['attributes'].values())


def test_faa_command_refuses_changed_provenance_without_publishing_output(tmp_path, monkeypatch):
    output = tmp_path / 'codebook.json'
    monkeypatch.setattr(sys, 'argv', ['import_faa_codes', '--archive', str(ARCHIVE),
                                    '--expected-sha256', '0' * 64, '--output', str(output)])
    with pytest.raises(SystemExit, match='Official archive changed'):
        runpy.run_module('investigation.experiments.import_faa_codes', run_name='__main__')
    assert not output.exists()


def test_faa_command_writes_only_the_checksum_matched_archive(tmp_path, monkeypatch):
    output = tmp_path / 'codebook.json'
    expected = json.loads(CODEBOOK.read_text())
    monkeypatch.setattr(sys, 'argv', ['import_faa_codes', '--archive', str(ARCHIVE),
                                    '--expected-sha256', expected['archive_sha256'], '--output', str(output)])
    runpy.run_module('investigation.experiments.import_faa_codes', run_name='__main__')
    actual = json.loads(output.read_text())
    assert actual['attributes'] == expected['attributes']
    assert actual['archive_sha256'] == hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()


def synthetic_workbook(*, header='Description', duplicate=False, incomplete=False, shared=False, absolute=False):
    """Minimal synthetic XLSX container; never a replacement for FAA source data."""
    buffer = io.BytesIO()
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(buffer, 'w') as book:
        book.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Synthetic" sheetId="1" r:id="r1"/></sheets></workbook>')
        target = '/xl/worksheets/sheet1.xml' if absolute else 'worksheets/sheet1.xml'
        book.writestr('xl/_rels/workbook.xml.rels', f'<Relationships><Relationship Id="r1" Target="{target}"/></Relationships>')
        if shared:
            book.writestr('xl/sharedStrings.xml', f'<sst xmlns="{ns}"><si><t>{header}</t></si><si><r><t>Synthetic </t></r><r><t>label</t></r></si></sst>')
            heading = '<c r="B1" t="s"><v>0</v></c>'
            label = '<c r="B2" t="s"><v>1</v></c>'
        else:
            heading = f'<c r="B1" t="inlineStr"><is><t>{header}</t></is></c>'
            label = '<c r="B2" t="inlineStr"><is><t>Synthetic label</t></is></c>'
        row = '<row r="2"><c r="A2"><v>42</v></c>' + ('' if incomplete else label) + '</row>'
        duplicate_row = '<row r="3"><c r="A3"><v>42</v></c><c r="B3" t="inlineStr"><is><t>Duplicate</t></is></c></row>' if duplicate else ''
        book.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetData><row r="1">{heading}</row>{row}{duplicate_row}<row r="4"/></sheetData></worksheet>')
    return buffer.getvalue()


@pytest.mark.parametrize('shared,absolute', [(False, False), (True, True)])
def test_lookup_reader_preserves_shared_inline_and_numeric_cells(shared, absolute):
    sheet, rows = workbook_cells(synthetic_workbook(shared=shared, absolute=absolute))
    assert sheet == 'Synthetic'
    assert rows == [{'B': 'Description'}, {'A': '42', 'B': 'Synthetic label'}, {}]


@pytest.mark.parametrize('failure,expected_error', [('missing', 'one official lookup'),
                                                ('header', 'lookup header'),
                                                ('duplicate', 'duplicate'),
                                                ('incomplete', 'Incomplete')])
def test_lookup_extraction_rejects_missing_malformed_or_ambiguous_rows(tmp_path, failure, expected_error):
    archive = tmp_path / 'synthetic.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        for i, suffix in enumerate(TABLES.values()):
            if failure == 'missing' and i == 0:
                continue
            bundle.writestr('synthetic_' + suffix + '.xlsx', synthetic_workbook(
                header='Unexpected' if failure == 'header' else 'Description',
                duplicate=failure == 'duplicate', incomplete=failure == 'incomplete'))
    with pytest.raises(ValueError, match=expected_error):
        extract(archive)


def write_corpus(path, parts, year=2023):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        for i, part in enumerate(parts):
            row = dict.fromkeys(COLUMNS, '')
            row.update(OperatorControlNumber=f'SYNTHETIC{i:06d}', RegistryNNumber='N-SYNTHETIC',
                       SubmissionDate=f'{year}-02-01T00:00:00Z', DifficultyDate=f'01/01/{year}',
                       PartName=part, Discrepancy='Synthetic fixture narrative.')
            writer.writerow(row)


def test_vocabulary_fit_normalizes_parts_excludes_unknowns_and_preserves_existing_output(tmp_path):
    source, output = tmp_path / 'fit.csv', tmp_path / 'parts.json'
    write_corpus(source, ['z pump', ' A valve ', 'z pump', 'UNKNOWN', 'N/A', ''])
    result = fit(source, output)
    assert result['parts'] == ['A VALVE', 'Z PUMP']
    assert result['fit_years'] == [2023]
    assert result['parts_sha256'] == hashlib.sha256(b'["A VALVE","Z PUMP"]').hexdigest()
    assert json.loads(output.read_text()) == result
    original = output.read_bytes()
    with pytest.raises(FileExistsError, match='Preserve'):
        fit(source, output)
    assert output.read_bytes() == original


@pytest.mark.parametrize('year', [2024, 2025])
def test_vocabulary_fit_refuses_selection_or_held_out_data_without_output(tmp_path, year):
    source, output = tmp_path / 'contaminated.csv', tmp_path / 'parts.json'
    write_corpus(source, ['SYNTHETIC PART'], year=year)
    with pytest.raises(ValueError, match='only 2023'):
        fit(source, output)
    assert not output.exists()


def test_vocabulary_command_exports_fit_only_metadata_and_refuses_empty_corpus(tmp_path, monkeypatch, capsys):
    source, output = tmp_path / 'fit.csv', tmp_path / 'parts.json'
    write_corpus(source, ['SYNTHETIC PART'])
    monkeypatch.setattr(sys, 'argv', ['fit_grounding_vocabulary', '--source', str(source), '--output', str(output)])
    runpy.run_module('investigation.experiments.fit_grounding_vocabulary', run_name='__main__')
    summary = json.loads(capsys.readouterr().out)
    assert summary == {'parts': 1, 'fit_years': [2023],
                       'corpus_sha256': json.loads(output.read_text())['corpus']['corpus_sha256']}
    empty = tmp_path / 'empty.csv'
    write_corpus(empty, [])
    with pytest.raises(ValueError, match='only 2023'):
        fit(empty, tmp_path / 'empty-output.json')
    assert not (tmp_path / 'empty-output.json').exists()
