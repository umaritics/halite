"""One live knowledge-time snapshot shared by managed ranking and question counts."""
from copy import deepcopy

from investigation.experiments.offline import Corpus, timestamp


class LiveGraphSnapshot:
    def __init__(self, repo, *, now, asset_id):
        if now.utcoffset() is None:
            raise ValueError('Live knowledge time must be timezone-aware.')
        self.now = now
        self.assets = repo.list_assets_with_counts()
        by_id = {a['id']: a for a in self.assets}
        by_tail = {a.get('tail_number'): a for a in self.assets}
        self.records, self.invalid = {}, 0
        for raw in repo.list_service_records():
            try:
                submitted = timestamp(str(raw.get('submitted_at') or ''))
                rid = str(raw['record_id']).strip().upper()
                if not rid:
                    raise ValueError('Missing record ID.')
            except (ValueError, KeyError):
                self.invalid += 1
                continue
            if rid in self.records:
                raise ValueError('Duplicate graph record IDs prevent a trustworthy snapshot.')
            asset = by_id.get(raw.get('asset_id')) or by_tail.get(raw.get('asset_key')) or by_tail.get(raw.get('tail_number')) or {}
            self.records[rid] = {**deepcopy(raw), 'record_id':rid,'submitted_at':submitted,
                'text':str(raw.get('text') or ''),'part_name':str(raw.get('part_name') or '').strip().upper(),
                'asset_key':str(raw.get('asset_key') or raw.get('tail_number') or '').strip().upper(),
                'occurred_at':str(raw.get('occurred_at') or ''),
                'aircraft_model':str(asset.get('make') or '').strip()+'/'+str(asset.get('model') or '').strip()}
        self.corpus = Corpus(self.records)
        self.visible_ids = {rid for rid,r in self.records.items() if r['submitted_at'] < now}
        # Real ABOUT membership, not an inferred relationship from a tail string.
        self.asset_ids = {str(r['record_id']).upper() for r in repo.list_asset_history(asset_id,limit=len(self.records)+self.invalid+1)} if asset_id else set()
        self.asset_id = asset_id
        self.ordered = sorted(self.visible_ids, key=lambda rid:(self.records[rid]['occurred_at'],rid), reverse=True)

    def _copy(self, rid):
        record = deepcopy(self.records[rid])
        record['submitted_at'] = record['submitted_at'].isoformat()
        known = {r['record_id'] for r in self.corpus.successors.get(rid, [])}
        corrected = record.get('corrected_by') or {}
        if corrected.get('record_id') in self.records:
            known.add(corrected['record_id'])
        visible = known & self.visible_ids
        if visible:
            record.update(status='superseded',is_superseded=True,superseding_record=sorted(visible)[0])
        elif known and record.get('status') == 'superseded':
            # Do not let a future correction change an earlier visible ranking.
            record.update(status='unscored',is_superseded=False)
            record.pop('superseding_record', None)
        if corrected.get('record_id') not in self.visible_ids:
            record.pop('corrected_by', None)
        return record

    def list_assets_with_counts(self):
        return deepcopy(self.assets)

    def list_service_records(self, status=None, asset_id=None, limit=None):
        if asset_id is not None and asset_id != self.asset_id:
            raise ValueError('Snapshot does not include that aircraft relationship scope.')
        ids = [rid for rid in self.ordered if asset_id is None or rid in self.asset_ids]
        if status is None:
            return [self._copy(rid) for rid in (ids if limit is None else ids[:limit])]
        rows = [self._copy(rid) for rid in ids]
        rows = [r for r in rows if r.get('status') == status]
        return rows if limit is None else rows[:limit]

    def list_asset_history_recent(self, asset_id, limit=30):
        return self.list_service_records(asset_id=asset_id,limit=limit)

    def get_service_record(self, record_id):
        return self._copy(record_id) if record_id in self.visible_ids else None

    def get_service_records_by_ids(self, record_ids):
        return [self._copy(rid) for rid in record_ids if rid in self.visible_ids]
