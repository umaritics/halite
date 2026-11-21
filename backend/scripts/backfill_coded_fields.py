"""Restore raw FAA coded fields by exact record ID. Dry-run unless --apply is given.

Run against an operator-backed-up, quiescent graph. Existing nonempty conflicting
values are preserved and reported. A failed write exits nonzero; rerunning is
idempotent. This script performs no model calls or graph identity/link changes.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIELDS = {
    'stage_of_operation': 'StageOfOperationCode',
    'how_discovered': 'HowDiscoveredCode',
    'nature_of_condition': 'NatureOfConditionA',
    'precautionary_procedure': 'PrecautionaryProcedureA',
}


def load_source(path):
    """Validate the entire source before any graph access/write; preserve raw strings."""
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    records = {}
    duplicates = 0
    with opener(path, 'rt', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'OperatorControlNumber', *FIELDS.values()}
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not required <= set(reader.fieldnames):
            raise ValueError('CSV requires unique OperatorControlNumber and all four coded-field columns.')
        for line, row in enumerate(reader, 2):
            if None in row or any(row.get(key) is None for key in required):
                raise ValueError(f'Malformed CSV row {line}.')
            rid = row['OperatorControlNumber'].strip()
            if not rid:
                raise ValueError(f'Blank OperatorControlNumber at row {line}.')
            values = {key: row[column].strip() for key, column in FIELDS.items()}
            if rid in records:
                if values != records[rid]:
                    raise ValueError(f'Conflicting duplicate OperatorControlNumber: {rid}. No backfill applied.')
                duplicates += 1
            records[rid] = values
    if not records:
        raise ValueError('CSV has no data records.')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return records, {'source_sha256': digest.hexdigest(), 'source_records': len(records), 'identical_duplicate_rows': duplicates}


def backfill(repo, records, *, apply=False):
    # Build the complete plan before writes, with exact-ID matching only.
    plans, missing, conflicts, unchanged = [], [], [], 0
    for rid, values in records.items():
        current = repo.get_service_record(rid)
        if current is None:
            missing.append(rid)
            continue
        updates, before = {}, {}
        for field, value in values.items():
            existing = current.get(field)
            if value and existing != value:
                if existing is not None and existing != '':
                    conflicts.append({'record_id': rid, 'field': field, 'existing': existing, 'source': value})
                else:
                    updates[field], before[field] = value, existing
        if updates:
            plans.append({'record_id': rid, 'before': before, 'updates': updates})
        else:
            unchanged += 1
    changed = 0
    if apply:
        for plan in plans:
            result = repo.update_service_record(plan['record_id'], plan['updates'])
            if result is None or any(result.get(key) != value for key, value in plan['updates'].items()):
                raise RuntimeError(f"Backfill verification failed at {plan['record_id']}; earlier updates may have applied. Retry is idempotent.")
            changed += 1
    return {'mode': 'apply' if apply else 'dry_run', 'source_records': len(records),
            'matched_records': len(records) - len(missing), 'unchanged_records': unchanged,
            'would_update_records': len(plans), 'updated_records': changed,
            'would_update_fields': sum(len(p['updates']) for p in plans),
            'missing_record_ids': missing, 'conflicts': conflicts, 'changes': plans}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True, help='Original FAA CSV or CSV.gz with all coded columns')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Plan only (the default)')
    mode.add_argument('--apply', action='store_true', help='Apply the planned missing-value updates')
    args = parser.parse_args(argv)
    records, provenance = load_source(args.csv)
    # Validate input before connecting, and never silently select a demo graph.
    from config import settings
    from graph.neo4j_client import Neo4jClient
    from graph.queries import GraphRepository
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    try:
        print(json.dumps({**backfill(GraphRepository(client), records, apply=args.apply), **provenance}, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    main()
