"""Incremental visible-report counts with query-chain removal at every knowledge time."""
from collections import Counter

from investigation.attributes import read_attributes
from investigation.questions import likelihood_from_counts


def known_model(value):
    value = str(value or '').strip()
    pieces = value.split('/')
    return value if all(p.strip().upper() not in ('', 'UNKNOWN', 'NONE', 'N/A') for p in pieces) else None


class TemporalQuestionIndex:
    def __init__(self, corpus, schema):
        self.corpus, self.schema = corpus, schema
        self.ordered = sorted(corpus.records.values(), key=lambda r: (r['submitted_at'], r['record_id']))
        self.values = {r['record_id']: read_attributes(r, schema) for r in self.ordered}
        self.chains = {}
        for rid, chain in corpus.chains.items():
            self.chains.setdefault(chain, []).append(rid)
        self.fleet = {key: Counter() for key in schema['domains']}
        self.parts, self.models = {}, {}
        self.cursor = 0
        self.last_time = None

    def _apply(self, record, delta):
        part = record['part_name'].strip().upper()
        model = known_model(record.get('aircraft_model'))
        part_counts = self.parts.setdefault(part, {key: Counter() for key in self.fleet})
        model_counts = self.models.setdefault((model, part), {key: Counter() for key in self.fleet}) if model else None
        for attribute, value in self.values[record['record_id']].items():
            self.fleet[attribute][value] += delta
            part_counts[attribute][value] += delta
            if model_counts is not None:
                model_counts[attribute][value] += delta

    def for_query(self, query_id, names):
        query = self.corpus.records[query_id]
        cutoff = query['submitted_at']
        if self.last_time is not None and cutoff < self.last_time:
            raise ValueError('Temporal index queries must be ordered by submission time.')
        while self.cursor < len(self.ordered) and self.ordered[self.cursor]['submitted_at'] < cutoff:
            self._apply(self.ordered[self.cursor], 1)
            self.cursor += 1
        self.last_time = cutoff
        excluded = [self.corpus.records[rid] for rid in self.chains[self.corpus.chains[query_id]]
                    if self.corpus.records[rid]['submitted_at'] < cutoff]
        for record in excluded:
            self._apply(record, -1)
        try:
            model = known_model(query.get('aircraft_model'))
            result = {}
            for attribute, domain in self.schema['domains'].items():
                parts = {name.strip().upper(): self.parts.get(name.strip().upper(), {}).get(attribute, Counter()) for name in names}
                local = {name.strip().upper(): self.models.get((model, name.strip().upper()), {}).get(attribute, Counter()) for name in names} if model else {}
                result[attribute] = likelihood_from_counts(domain, names, self.fleet[attribute], parts, local)
            audit = {'knowledge_time': cutoff.isoformat(), 'n_visible_records': sum(next(iter(self.fleet.values())).values()),
                     'excluded_earlier_chain_ids': sorted(r['record_id'] for r in excluded),
                     'strict_submission_bound': True, 'query_chain_excluded': True}
        finally:
            for record in excluded:
                self._apply(record, 1)
        return result, audit
