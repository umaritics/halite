"""Fixed askable report attributes; official code descriptions are data, never guesses."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

CODED = ('stage_of_operation', 'how_discovered', 'nature_of_condition', 'precautionary_procedure')
OTHER = '__OTHER__'
NOT_SURE = 'not_sure'
CUES = {
    'intermittent': r'\bintermittent\w*\b',
    'leak': r'\bleak\w*\b',
    'smoke_or_odour': r'\b(?:smoke|smoky|fumes?|odou?rs?)\b',
    'noise_or_vibration': r'\b(?:nois\w*|vibrat\w*)\b',
    'warning_message': r'\b(?:warning|annunciat\w*|eicas|ecam)\b',
    'found_during_inspection': r'\b(?:inspect\w*|inspection|routine check)\b',
    'after_recent_maintenance': r'\b(?:after|following|since)\b.{0,60}\b(?:maintenance|repair|replacement|overhaul)\b',
}
CUE_PATTERNS = {key: re.compile(pattern, re.I) for key, pattern in CUES.items()}
TEXTS = {
    'stage_of_operation': 'At what stage of operation was the difficulty discovered?',
    'how_discovered': 'How was the difficulty discovered?',
    'nature_of_condition': 'Which nature-of-condition code was recorded?',
    'precautionary_procedure': 'Which precautionary procedure code was recorded?',
    'part_condition': 'Which part condition was recorded in the initial report?',
    'location_zone': 'Which hundred-level location zone was recorded?',
}


def load_codebook(path=None):
    path = Path(path) if path else Path(__file__).parent / 'data/faa_codes.json'
    data = json.loads(path.read_text())
    if not data.get('source', '').startswith('https://sdrs.faa.gov/') or not data.get('archive_sha256'):
        raise ValueError('FAA codebook source provenance is required.')
    for key in CODED:
        table = data['attributes'][key]
        if not table.get('file_sha256') or not isinstance(table.get('values'), dict) or not table['values']:
            raise ValueError('Incomplete FAA lookup table.')
        if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in table['values'].items()):
            raise ValueError('Codebook values must be nonempty strings.')
    return data


def fit_schema(records, *, corpus_sha256, codebook=None):
    records = list(records)
    if not records or any(r.get('year') != 2023 for r in records):
        raise ValueError('Attribute vocabulary is fitted on 2023 records only.')
    codebook = codebook or load_codebook()
    counts = Counter(str(r.get('part_condition', '')).strip().upper() for r in records)
    counts.pop('', None)
    common = [value for value, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:30]]
    domains = {key: list(codebook['attributes'][key]['values']) + [OTHER] for key in CODED}
    domains.update(part_condition=common + [OTHER], location_zone=[str(i) for i in range(100, 1000, 100)] + [OTHER])
    domains.update({key: ['mentioned', 'not_mentioned'] for key in CUES})
    return {'schema_version': 'report-attributes-v1', 'fit_years': [2023], 'corpus_sha256': corpus_sha256,
            'codebook_sha256': hashlib.sha256(json.dumps(codebook, sort_keys=True).encode()).hexdigest(),
            'domains': domains, 'part_condition_top30': common,
            'cue_semantics': 'Token/pattern mention in original narrative, including a negated mention; absence means not mentioned, never a confirmed negative finding.'}


def read_attributes(record, schema):
    values = {}
    for key in CODED:
        raw = str(record.get(key, '') or '').strip()
        values[key] = raw if raw in schema['domains'][key] else OTHER
    raw = str(record.get('part_condition', '') or '').strip().upper()
    values['part_condition'] = raw if raw in schema['domains']['part_condition'] else OTHER
    zone = re.search(r'\b(?:ZONE|ZN)\s*[-:]?\s*([1-9])\d{2}\b', str(record.get('part_location', '')).upper())
    values['location_zone'] = zone[1] + '00' if zone else OTHER
    text = str(record.get('text', '') or '')
    for key, pattern in CUE_PATTERNS.items():
        values[key] = 'mentioned' if pattern.search(text) else 'not_mentioned'
    return values


def option_label(attribute, value, codebook):
    if value == OTHER:
        return 'Other / not recorded'
    if attribute in CODED:
        # Missing code descriptions cannot be supplied from model/general knowledge.
        return f"{codebook['attributes'][attribute]['values'][value]} ({value})"
    if attribute == 'location_zone':
        return 'Zone ' + value
    if value in ('mentioned', 'not_mentioned'):
        return 'Mentioned in the initial report' if value == 'mentioned' else 'Not mentioned in the initial report'
    return value


def question_text(attribute):
    if attribute in TEXTS:
        return TEXTS[attribute]
    if attribute not in CUES:
        raise ValueError('Unknown question attribute.')
    label = attribute.replace('_', ' ')
    return f'Was {label} mentioned in the initial report (including a negative finding)?'
