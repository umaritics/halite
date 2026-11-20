import pytest

from investigation.experiments.offline import Corpus, ranked_cases, timestamp


def record(rid, submitted, *, part='PUMP', text='hydraulic pressure loss', tail='N-TEST'):
    return {'record_id': rid, 'submitted_at': timestamp(submitted), 'occurred_at': '2023-01-01',
            'year': 2023, 'asset_key': tail, 'part_name': part, 'text': text, 'jasc_code': '2900'}


def test_visibility_uses_strict_aware_submission_not_occurrence_or_string_order():
    records = [
        record('QUERY001', '2023-03-01T10:00:00+00:00'),
        # Lexicographically earlier, but actually one hour after query.
        record('FUTURE01', '2023-03-01T06:00:00-05:00'),
        record('EQUAL001', '2023-03-01T05:00:00-05:00'),
        # Lexicographically later, but one hour before query.
        record('VISIBLE1', '2023-03-01T11:00:00+02:00'),
    ]
    corpus = Corpus({r['record_id']: r for r in records})
    graph = corpus.view('QUERY001')
    assert [r['record_id'] for r in graph.list_service_records()] == ['VISIBLE1']
    assert graph.get_service_records_by_ids(['FUTURE01', 'QUERY001', 'EQUAL001']) == []
    assert graph.used_ids == {'VISIBLE1'}
    with pytest.raises(ValueError, match='timezone'):
        timestamp('2023-03-01T10:00:00')


def test_entire_citation_chain_is_excluded_including_older_ancestor_and_future_correction():
    rows = [record('ROOT0001', '2023-01-01T00:00:00Z'),
            record('QUERY001', '2023-02-01T00:00:00Z', text='SUPPLEMENTAL REPORT FOR (ROOT0001): pressure loss'),
            record('ANSWER01', '2023-03-01T00:00:00Z', text='SUPPLEMENTAL REPORT FOR (QUERY001): sensor found', part='SENSOR'),
            record('OTHER001', '2023-01-02T00:00:00Z', tail='N-OTHER')]
    corpus = Corpus({r['record_id']: r for r in rows})
    graph = corpus.view('QUERY001')
    assert [r['record_id'] for r in graph.list_service_records()] == ['OTHER001']
    assert graph.list_asset_history_recent('N-TEST') == []
    with pytest.raises(AssertionError):
        graph._copy(corpus.records['ROOT0001'])
    cases = ranked_cases(corpus, 2023)
    case = next(c for c in cases if c['query_id'] == 'QUERY001')
    assert case['answer_part'] == 'SENSOR'
    assert {rid for h in case['hypotheses'] for rid in h['evidence_record_ids']} == {'OTHER001'}
    assert all(h['part_name'] != 'SENSOR' for h in case['hypotheses'])


def test_supersession_status_is_known_only_when_correction_was_submitted():
    rows = [record('QUERY001', '2023-02-01T00:00:00Z'),
            record('OLDER001', '2023-01-01T00:00:00Z', tail='N-OTHER'),
            record('CORRECT1', '2023-03-01T00:00:00Z', tail='N-OTHER', text='SUPPLEMENTAL REPORT FOR (OLDER001)')]
    corpus = Corpus({r['record_id']: r for r in rows})
    assert corpus.view('QUERY001').get_service_records_by_ids(['OLDER001'])[0]['status'] == 'auto_accepted'
    corpus.records['QUERY001']['submitted_at'] = timestamp('2023-04-01T00:00:00Z')
    assert corpus.view('QUERY001').get_service_records_by_ids(['OLDER001'])[0]['status'] == 'superseded'


def test_bad_tail_and_nonforward_citations_never_form_labels_or_chains():
    rows = [record('QUERY001', '2023-02-01T00:00:00Z'),
            record('WRONG001', '2023-03-01T00:00:00Z', tail='N-OTHER', text='SUPPLEMENTAL REPORT FOR (QUERY001)'),
            record('WRONG002', '2023-01-01T00:00:00Z', text='SUPPLEMENTAL REPORT FOR (QUERY001)')]
    corpus = Corpus({r['record_id']: r for r in rows})
    assert corpus.pairs == []
    assert corpus.discards['tail_mismatch_or_empty'] == 1
    assert corpus.discards['nonforward_submission'] == 1


def test_all_known_corrections_are_retained_not_just_the_first():
    rows = [record('QUERY001', '2023-01-01T00:00:00Z'),
            record('CORRECT1', '2023-02-01T00:00:00Z', text='SUPPLEMENTAL REPORT FOR (QUERY001)', part='SENSOR'),
            record('CORRECT2', '2023-03-01T00:00:00Z', text='SUPPLEMENTAL REPORT FOR (QUERY001)', part='PUMP'),
            record('CORRECT3', '2023-04-01T00:00:00Z', text='SUPPLEMENTAL REPORT FOR (QUERY001)', part='UNKNOWN')]
    corpus = Corpus({r['record_id']: r for r in rows})
    assert corpus.cases(2023) == [('QUERY001', 'CORRECT1'), ('QUERY001', 'CORRECT2')]
