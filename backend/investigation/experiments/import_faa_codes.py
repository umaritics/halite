"""Extract official FAA lookup cells using only the standard library; preserve wording."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
import zipfile

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
TABLES = {'stage_of_operation': 'StageofOperation', 'how_discovered': 'HowDiscovered',
          'nature_of_condition': 'NatureofCondition', 'precautionary_procedure': 'PrecautionCode'}
SOURCE = 'https://sdrs.faa.gov/Documents/SDRS%20Look-Up%20Tables.zip'


def workbook_cells(content):
    with zipfile.ZipFile(io.BytesIO(content)) as x:
        shared = []
        if 'xl/sharedStrings.xml' in x.namelist():
            shared = [''.join(node.itertext()) for node in ET.fromstring(x.read('xl/sharedStrings.xml')).findall('m:si', NS)]
        workbook = ET.fromstring(x.read('xl/workbook.xml'))
        sheet = workbook.find('m:sheets/m:sheet', NS)
        rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        relationships = ET.fromstring(x.read('xl/_rels/workbook.xml.rels'))
        target = next(r.attrib['Target'] for r in relationships if r.attrib['Id'] == rid)
        path = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        rows = []
        for row in ET.fromstring(x.read(path)).findall('m:sheetData/m:row', NS):
            cells = {}
            for cell in row.findall('m:c', NS):
                column = ''.join(c for c in cell.attrib['r'] if c.isalpha())
                value = cell.findtext('m:v', '', NS)
                if cell.attrib.get('t') == 's':
                    value = shared[int(value)]
                elif cell.attrib.get('t') == 'inlineStr':
                    value = ''.join(cell.find('m:is', NS).itertext())
                cells[column] = value
            rows.append(cells)
    return sheet.attrib['name'], rows


def extract(archive, *, retrieved_at_utc=None):
    content = Path(archive).read_bytes()
    output = {'source': SOURCE, 'archive_sha256': hashlib.sha256(content).hexdigest(),
              'source_kind': 'FAA official SDRS Look-up Tables download',
              'retrieved_at_utc': retrieved_at_utc or datetime.now(timezone.utc).date().isoformat(), 'attributes': {}}
    with zipfile.ZipFile(io.BytesIO(content)) as bundle:
        for attribute, suffix in TABLES.items():
            matches = [n for n in bundle.namelist() if n.endswith('_' + suffix + '.xlsx')]
            if len(matches) != 1:
                raise ValueError('Expected one official lookup workbook per attribute.')
            name = matches[0]
            raw = bundle.read(name)
            sheet, rows = workbook_cells(raw)
            if not rows or rows[0].get('B') != 'Description':
                raise ValueError('Unexpected FAA lookup header.')
            values = {}
            for row in rows[1:]:
                code, label = row.get('A', '').strip(), row.get('B', '').strip()
                if not code and not label:
                    continue
                if not code or not label or code in values:
                    raise ValueError('Incomplete or duplicate FAA lookup row.')
                values[code] = label
            output['attributes'][attribute] = {'file': name, 'file_sha256': hashlib.sha256(raw).hexdigest(),
                                               'sheet': sheet, 'range': f'A2:B{len(values)+1}', 'values': values}
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = extract(args.archive)
    if data['archive_sha256'] != args.expected_sha256:
        raise SystemExit('Official archive changed; review the new source rather than reusing old provenance.')
    Path(args.output).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
