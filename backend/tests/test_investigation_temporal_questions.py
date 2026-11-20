import pytest

from investigation.attributes import fit_schema
from investigation.experiments.offline import Corpus, timestamp
from investigation.experiments.temporal_questions import TemporalQuestionIndex
from investigation.questions import build_likelihoods


def record(rid, date, part='PUMP', stage='CL', text='pressure loss', model='M1'):
    return {'record_id':rid,'submitted_at':timestamp(date),'occurred_at':'2023-01-01','year':2023,
            'asset_key':'N1','aircraft_model':model,'part_name':part,'stage_of_operation':stage,'text':text}


def test_temporal_counts_exclude_future_equal_and_entire_query_chain():
    rows=[record('ANCEST01','2023-01-01T00:00:00Z',stage='CR'),
          record('PAST0001','2023-01-02T00:00:00Z',stage='CL'),
          record('QUERY001','2023-02-01T00:00:00Z',text='SUPPLEMENTAL REPORT FOR (ANCEST01)'),
          record('EQUAL001','2023-02-01T00:00:00Z',stage='CR'),
          record('FUTURE01','2023-03-01T00:00:00Z',stage='CR')]
    corpus=Corpus({r['record_id']:r for r in rows})
    s=fit_schema([rows[1]],corpus_sha256='a'*64)
    index=TemporalQuestionIndex(corpus,s)
    models,audit=index.for_query('QUERY001',['PUMP'])
    expected=build_likelihoods([rows[1]],['PUMP'],s,aircraft_model='M1')
    assert models==expected
    assert audit['n_visible_records']==1 and audit['excluded_earlier_chain_ids']==['ANCEST01']
    # Repeated query does not permanently subtract a chain or advance past equality.
    assert index.for_query('QUERY001',['PUMP'])[0]==models
    assert index.for_query('EQUAL001',['PUMP'])[1]['n_visible_records']==2
    with pytest.raises(ValueError,match='ordered'):
        index.for_query('PAST0001',['PUMP'])


def test_future_record_changes_cannot_change_likelihoods_or_questions():
    base=[record('PAST0001','2023-01-01T00:00:00Z'),record('QUERY001','2023-02-01T00:00:00Z')]
    s=fit_schema([base[0]],corpus_sha256='a'*64)
    a=TemporalQuestionIndex(Corpus({r['record_id']:r for r in base}),s).for_query('QUERY001',['PUMP'])[0]
    extended=base+[record('FUTURE01','2023-03-01T00:00:00Z',stage='CR',part='SENSOR',text='smoke leak')]
    b=TemporalQuestionIndex(Corpus({r['record_id']:r for r in extended}),s).for_query('QUERY001',['PUMP'])[0]
    assert a==b
