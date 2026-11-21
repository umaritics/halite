"""Verify actual backfill CLI against an explicitly configured disposable local Neo4j."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
from scripts.backfill_coded_fields import FIELDS


def main():
    uri = os.environ['NEO4J_URI']
    if urlparse(uri).hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('This synthetic proof must use a disposable local graph.')
    client = Neo4jClient(uri, os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD'])
    repo = GraphRepository(client)
    rid = 'CODECLI-' + uuid.uuid4().hex
    try:
        repo.create_service_record({'record_id': rid, 'part_name': 'PUMP', 'text': 'Unchanged evidence', 'confidence': .42})
        # Simulate a genuinely old node where the four properties do not exist.
        client.run_query('MATCH (s:ServiceRecord {record_id:$rid}) REMOVE s.stage_of_operation, s.how_discovered, s.nature_of_condition, s.precautionary_procedure', {'rid':rid})
        before = repo.get_service_record(rid)
        with TemporaryDirectory(prefix='halite-coded-cli-') as temp:
            source = Path(temp) / 'synthetic.csv'
            with source.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['OperatorControlNumber', *FIELDS.values()])
                writer.writeheader()
                writer.writerow({'OperatorControlNumber': rid, **dict(zip(FIELDS.values(), ['00', '01', '02', '03']))})
            def invoke(flag):
                run = subprocess.run([sys.executable, str(ROOT/'backend/scripts/backfill_coded_fields.py'), '--csv', str(source), flag],
                                     capture_output=True, text=True, check=True, cwd=ROOT/'backend')
                return json.loads(run.stdout)
            dry = invoke('--dry-run')
            assert dry['updated_records'] == 0 and dry['would_update_fields'] == 4
            assert repo.get_service_record(rid) == before
            applied = invoke('--apply')
            assert applied['updated_records'] == 1
            after = repo.get_service_record(rid)
            assert [after[f] for f in FIELDS] == ['00', '01', '02', '03']
            assert all(after[k] == v for k,v in before.items() if k != 'updated_at')
            repeat = invoke('--apply')
            assert repeat['updated_records'] == 0 and repo.get_service_record(rid) == after
        print(json.dumps({'synthetic_record_id':rid, 'source': 'synthetic fixture, not a student/human label',
                          'dry_run':dry, 'apply':applied, 'repeat':repeat, 'before':before, 'after':after,
                          'dry_run_unchanged':True,'other_properties_unchanged':True,'leading_zero_codes_preserved':True,
                          'second_apply_unchanged':True,'shared_staging_accessed':False}, indent=2))
    finally:
        client.run_query('MATCH (s:ServiceRecord {record_id:$rid}) DETACH DELETE s', {'rid':rid})
        client.close()


if __name__ == '__main__':
    main()
