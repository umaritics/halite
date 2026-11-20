"""Submission-time and citation-chain isolation for the original Mid-I ranker.

This consumes official/raw or V1 processed CSVs. It does not edit V1's corpus,
construct new retrieval features, or infer code meanings.
"""
from __future__ import annotations

import csv
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re

from investigation.experiments.download_projection import COLUMNS
from investigation.ranker_port import rank

CITATION = re.compile(r'SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*([A-Z0-9]{6,})\s*\)?', re.I)
OPEN = re.compile(r'\*{0,2}SUPPLEMENTAL\s+REPORT\s+WILL\s+BE\s+SUBMITTED\*{0,2}\s*\(OPEN\)?', re.I)
UNKNOWN = {'', 'UNKNOWN', 'NONE', 'N/A', 'UNK', 'NOT REPORTED'}


def timestamp(value):
    result = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('SubmissionDate must include a timezone.')
    return result


def load_records(paths):
    records, ambiguous = {}, set()
    stats = {'rows': 0, 'invalid': 0, 'duplicate_identical': 0, 'ambiguous_ids': 0}
    sources = []
    for path in map(Path, paths):
        digest = hashlib.sha256()
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt', encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            if not set(COLUMNS).issubset(reader.fieldnames or []):
                raise ValueError('Corpus is missing fields from the frozen projection.')
            for row in reader:
                projection = {key: row[key] for key in COLUMNS}
                digest.update((json.dumps(projection, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
                stats['rows'] += 1
                try:
                    rid = row['OperatorControlNumber'].strip().upper()
                    if not rid:
                        raise ValueError('Missing record ID.')
                    submitted = timestamp(row['SubmissionDate'])
                    occurred = datetime.strptime(row['DifficultyDate'].strip(), '%m/%d/%Y')
                except ValueError:
                    stats['invalid'] += 1
                    continue
                rec = {'record_id': rid, 'asset_key': row['RegistryNNumber'].strip().upper(),
                       'submitted_at': submitted, 'occurred_at': occurred.date().isoformat(),
                       'year': occurred.year, 'part_name': row['PartName'].strip().upper(),
                       'part_condition': row['PartCondition'].strip().upper(),
                       'part_location': row['PartLocation'].strip().upper(),
                       'jasc_code': row['JASCCode'].strip(), 'text': row['Discrepancy'].strip(),
                       'aircraft_model': row['AircraftMake'].strip() + '/' + row['AircraftModel'].strip(),
                       'stage_of_operation': row['StageOfOperationCode'].strip(),
                       'how_discovered': row['HowDiscoveredCode'].strip(),
                       'nature_of_condition': row['NatureOfConditionA'].strip(),
                       'precautionary_procedure': row['PrecautionaryProcedureA'].strip()}
                if rid in records:
                    if records[rid] == rec:
                        stats['duplicate_identical'] += 1
                    else:
                        ambiguous.add(rid)
                else:
                    records[rid] = rec
        meta_path = path.with_suffix(path.suffix + '.json')
        if meta_path.exists():
            expected = json.loads(meta_path.read_text())['projection_sha256']
            if expected != digest.hexdigest():
                raise ValueError('Corpus projection fingerprint does not match its download metadata.')
        sources.append({'file': path.name, 'projection_sha256': digest.hexdigest()})
    for rid in ambiguous:
        records.pop(rid, None)
    stats['ambiguous_ids'] = len(ambiguous)
    stats['records'] = len(records)
    fingerprint = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    return records, {'sources': sources, 'corpus_sha256': fingerprint, **stats}


class Corpus:
    def __init__(self, records):
        self.records = records
        parents = {rid: rid for rid in records}
        def root(rid):
            while parents[rid] != rid:
                parents[rid] = parents[parents[rid]]
                rid = parents[rid]
            return rid
        self.pairs = []
        self.successors = {}
        self.discards = {'missing_id': 0, 'tail_mismatch_or_empty': 0, 'nonforward_submission': 0}
        seen = set()
        for new in records.values():
            for old_id in CITATION.findall(new['text']):
                old_id = old_id.upper()
                old = records.get(old_id)
                if old is None:
                    self.discards['missing_id'] += 1
                    continue
                if not new['asset_key'] or old['asset_key'] != new['asset_key']:
                    self.discards['tail_mismatch_or_empty'] += 1
                    continue
                if new['submitted_at'] <= old['submitted_at']:
                    self.discards['nonforward_submission'] += 1
                    continue
                pair = (old_id, new['record_id'])
                if pair in seen:
                    continue
                seen.add(pair)
                parents[root(new['record_id'])] = root(old_id)
                self.successors.setdefault(old_id, []).append(new)
                self.pairs.append(pair)
        self.chains = {rid: root(rid) for rid in records}
        self.sorted_records = sorted(records.values(), key=lambda r: (r['occurred_at'], r['record_id']), reverse=True)

    def view(self, query_id):
        return VisibleGraph(self, query_id)

    def cases(self, year):
        # Every eligible correction pair is a case, including multiple corrections
        # of one original. Cluster bootstrap keeps their dependence explicit.
        return sorted((old_id, new_id) for old_id, new_id in self.pairs
                      if self.records[old_id]['year'] == year
                      and self.records[new_id]['part_name'] not in UNKNOWN)


class VisibleGraph:
    def __init__(self, corpus, query_id):
        self.corpus = corpus
        self.query = corpus.records[query_id]
        self.used_ids = set()

    def _visible(self, record):
        return (record['submitted_at'] < self.query['submitted_at']
                and self.corpus.chains[record['record_id']] != self.corpus.chains[self.query['record_id']])

    def _copy(self, record):
        if not self._visible(record):
            raise AssertionError('Temporal or citation-chain leakage.')
        self.used_ids.add(record['record_id'])
        corrections = [r for r in self.corpus.successors.get(record['record_id'], []) if self._visible(r)]
        current = dict(record, status='superseded' if corrections else 'auto_accepted')
        if corrections:
            current['superseding_record'] = min(corrections, key=lambda r: r['submitted_at'])['record_id']
        return current

    def list_service_records(self, limit=2500):
        result = []
        for record in self.corpus.sorted_records:
            if self._visible(record):
                result.append(self._copy(record))
                if len(result) >= limit:
                    break
        return result

    def list_asset_history_recent(self, asset_id, limit=50):
        result = []
        for record in self.corpus.sorted_records:
            if record['asset_key'] == asset_id and self._visible(record):
                result.append(self._copy(record))
                if len(result) >= limit:
                    break
        return result

    def get_service_records_by_ids(self, ids):
        return [self._copy(self.corpus.records[rid]) for rid in ids
                if rid in self.corpus.records and self._visible(self.corpus.records[rid])]


def ranked_cases(corpus, year):
    cases = []
    for old_id, new_id in corpus.cases(year):
        original, correction = corpus.records[old_id], corpus.records[new_id]
        graph = corpus.view(old_id)
        # Remove known administrative marker only; no correction text or answer fields enter the query.
        symptom = OPEN.sub('', original['text']).strip()
        result = rank(graph, asset_id=original['asset_key'], symptoms=[symptom])
        old_part, new_part = original['part_name'], correction['part_name']
        category = ('same' if old_part == new_part else 'unknown_to_named' if old_part in UNKNOWN else 'named_to_named')
        cases.append({'case_id': old_id + '->' + new_id, 'query_id': old_id, 'answer_id': new_id,
                      'year': original['year'], 'answer_part': new_part, 'part_change': category,
                      'ranker_version': result['ranker_version'], 'hypotheses': result['hypotheses'],
                      'retrieval_audit': {'n_records_scanned': len(graph.used_ids), 'knowledge_time': original['submitted_at'].isoformat(),
                                          'query_chain_excluded': True, 'strict_submission_bound': True}})
    return cases
