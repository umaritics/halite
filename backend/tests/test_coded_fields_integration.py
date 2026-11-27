"""Exact raw-code round-trip and conservative/idempotent backfill on both stores."""
import csv
import gzip
import os
import uuid

import pytest

from agents.maintenance_agent import MaintenanceAgent
from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from scripts.backfill_coded_fields import FIELDS, backfill, load_source


@pytest.fixture(params=['memory', 'neo4j'])
def coded_repo(request):
    if request.param == 'memory':
        yield GraphRepository(MemoryGraphStore())
        return
    if not os.environ.get('NEO4J_URI') or not os.environ.get('NEO4J_PASSWORD'):
        pytest.skip('NEO4J_URI and NEO4J_PASSWORD required for real coded-field round-trip')
    from graph.neo4j_client import Neo4jClient
    # When configured, connectivity failures fail rather than turn into a pass.
    client = Neo4jClient(os.environ['NEO4J_URI'], os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD'])
    repo = GraphRepository(client)
    yield repo
    # Touch only records/assets tagged by this test's unique prefix.
    client.run_query("MATCH (n) WHERE n.record_id STARTS WITH 'CODETEST-' OR n.tail_number STARTS WITH 'CODETEST-' DETACH DELETE n")
    client.close()


def write_csv(path, rows):
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def raw_row():
    token = 'CODETEST-' + uuid.uuid4().hex
    return {'OperatorControlNumber': token, 'RegistryNNumber': token,
            'DifficultyDate': '02/03/2023', 'SubmissionDate': '02/04/2023',
            'PartName': 'PUMP', 'PartCondition': 'WORN', 'Discrepancy': 'No smoke; pressure loss',
            'StageOfOperationCode': ' 00 ', 'HowDiscoveredCode': ' 01 ',
            'NatureOfConditionA': ' 02 ', 'PrecautionaryProcedureA': ' 03 '}


def test_csv_ingest_round_trip_preserves_strings_and_duplicate_behavior(coded_repo, tmp_path):
    row = raw_row()
    source = tmp_path / 'input.csv'
    write_csv(source, [row])
    agent = MaintenanceAgent(coded_repo)
    assert agent.run({'csv_path': str(source)})['records_created'] == 1
    rid = row['OperatorControlNumber']
    saved = coded_repo.get_service_record(rid)
    for field, column in FIELDS.items():
        assert saved[field] == row[column].strip()
    assert saved['submitted_at'] == row['SubmissionDate']
    row['StageOfOperationCode'] = 'DIFFERENT'
    assert agent.run({'records': [row]})['duplicates_skipped'] == 1
    assert coded_repo.get_service_record(rid) == saved
    assert coded_repo.list_asset_history(coded_repo.find_or_create_asset(row['RegistryNNumber'])['id'])[0]['stage_of_operation'] == '00'


def test_missing_optional_codes_default_empty(coded_repo):
    row = raw_row()
    for column in FIELDS.values():
        row.pop(column)
    MaintenanceAgent(coded_repo).run({'records': [row]})
    assert all(coded_repo.get_service_record(row['OperatorControlNumber'])[field] == '' for field in FIELDS)


def test_backfill_dry_run_apply_idempotence_missing_and_conflicts(coded_repo, tmp_path):
    row = raw_row()
    rid = row['OperatorControlNumber']
    coded_repo.create_service_record({'record_id': rid, 'text': 'Original evidence', 'part_name': 'PUMP',
                                     'confidence': .42, 'stage_of_operation': 'CR', 'nature_of_condition': '02'})
    source = tmp_path / 'backfill.csv'
    write_csv(source, [row, {**row, 'OperatorControlNumber': rid + '-MISSING'}])
    rows, meta = load_source(source)
    assert meta['source_records'] == 2 and len(meta['source_sha256']) == 64
    before = coded_repo.get_service_record(rid)
    dry = backfill(coded_repo, rows)
    assert dry['would_update_records'] == 1 and dry['would_update_fields'] == 2
    assert dry['updated_records'] == 0 and dry['missing_record_ids'] == [rid + '-MISSING']
    assert dry['conflicts'] == [{'record_id': rid, 'field': 'stage_of_operation', 'existing': 'CR', 'source': '00'}]
    assert coded_repo.get_service_record(rid) == before
    applied = backfill(coded_repo, rows, apply=True)
    assert applied['updated_records'] == 1
    after = coded_repo.get_service_record(rid)
    for field in before:
        if field not in ('how_discovered', 'precautionary_procedure', 'updated_at'):
            assert after[field] == before[field]
    assert after['how_discovered'] == '01' and after['precautionary_procedure'] == '03'
    repeated = backfill(coded_repo, rows, apply=True)
    assert repeated['updated_records'] == 0 and repeated['would_update_fields'] == 0
    assert coded_repo.get_service_record(rid) == after
    # Blank source fields cannot erase a prior code.
    assert backfill(coded_repo, {rid: dict.fromkeys(FIELDS, '')}, apply=True)['updated_records'] == 0


def test_source_validation_rejects_conflicting_duplicates_before_graph_access(tmp_path):
    row = raw_row()
    source = tmp_path / 'duplicates.csv'
    write_csv(source, [row, {**row, 'HowDiscoveredCode': '99'}])
    with pytest.raises(ValueError, match='Conflicting duplicate'):
        load_source(source)
    write_csv(source, [row, row])
    assert load_source(source)[1]['identical_duplicate_rows'] == 1
    with gzip.open(tmp_path / 'source.csv.gz', 'wb') as stream:
        stream.write(source.read_bytes())
    assert load_source(tmp_path / 'source.csv.gz')[0] == load_source(source)[0]


@pytest.mark.parametrize('text', [
    'OperatorControlNumber\nID1\n',
    'OperatorControlNumber,StageOfOperationCode,HowDiscoveredCode,NatureOfConditionA,PrecautionaryProcedureA\n,CL,01,02,03\n',
    'OperatorControlNumber,StageOfOperationCode,HowDiscoveredCode,NatureOfConditionA,PrecautionaryProcedureA\nID1,CL\n',
    'OperatorControlNumber,StageOfOperationCode,HowDiscoveredCode,NatureOfConditionA,PrecautionaryProcedureA\n',
])
def test_invalid_sources_fail_before_write(tmp_path, text):
    source = tmp_path / 'invalid.csv'
    source.write_text(text)
    with pytest.raises(ValueError):
        load_source(source)


def test_failed_update_is_explicit_and_never_claimed_success():
    class FailedRepo:
        def get_service_record(self, rid):
            return {'record_id': rid}

        def update_service_record(self, rid, values):
            return None
    with pytest.raises(RuntimeError, match='earlier updates may have applied'):
        backfill(FailedRepo(), {'R1': {'stage_of_operation': 'CL'}}, apply=True)


def test_cli_validates_before_connecting_and_closes_client(tmp_path, monkeypatch, capsys):
    from scripts import backfill_coded_fields as tool
    from graph import neo4j_client
    source = tmp_path / 'cli.csv'
    source.write_text('wrong\nheader\n')
    calls = []
    class Client:
        def close(self):
            calls.append('close')
    monkeypatch.setattr(neo4j_client, 'Neo4jClient', lambda *args: calls.append('connect') or Client())
    with pytest.raises(ValueError):
        tool.main(['--csv', str(source)])
    assert calls == []
    row = raw_row()
    write_csv(source, [row])
    class Repo:
        def get_service_record(self, rid):
            return None
    monkeypatch.setattr('graph.queries.GraphRepository', lambda client: Repo())
    tool.main(['--csv', str(source), '--dry-run'])
    import json
    result = json.loads(capsys.readouterr().out)
    assert result['mode'] == 'dry_run' and result['missing_record_ids'] == [row['OperatorControlNumber']]
    assert calls == ['connect', 'close']
