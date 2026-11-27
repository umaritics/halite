"""Hand-calculated entropy/gain/posterior and honest report attribute semantics."""
from collections import Counter
import math
import random

import pytest

from investigation.attributes import CODED, CUES, NOT_SURE, OTHER, fit_schema, load_codebook, option_label, read_attributes
from investigation.questions import answer_question, build_likelihoods, expected_information_gain, likelihood_from_counts, posterior, select_question


def schema():
    return fit_schema([{'year': 2023, 'part_condition': 'CRACKED'}], corpus_sha256='a' * 64)


def test_hand_computed_three_bucket_gain():
    # Three equally likely buckets. X identifies the first; Y leaves two equal.
    # H(before)=log2(3), E[H(after)]=(1/3)*0+(2/3)*1. Gain=0.918295834 bits.
    prior = [1/3, 1/3, 1/3]
    matrix = [[1, 0], [0, 1], [0, 1]]
    assert expected_information_gain(prior, matrix) == pytest.approx(math.log2(3) - 2/3)
    assert posterior(prior, matrix, 0) == [1, 0, 0]
    assert posterior(prior, matrix, 1) == [0, .5, .5]


def test_uninformative_attribute_and_zero_prior_have_zero_gain():
    assert expected_information_gain([.2, .3, .5], [[.8, .2]] * 3) == pytest.approx(0)
    assert expected_information_gain([1, 0], [[.5, .5], [1, 0]]) == 0


@pytest.mark.parametrize('prior,matrix', [([.1, .1], [[1, 0], [0, 1]]), ([.5, .5], [[.2, .2], [0, 1]]),
                                       ([1], [[float('nan'), 0]]), ([.5, .5], [[1], [0, 1]])])
def test_invalid_distributions_fail(prior, matrix):
    with pytest.raises(ValueError):
        expected_information_gain(prior, matrix)


def test_dirichlet_smoothing_and_other_are_hand_computed():
    # fleet X/Y=.5/.5, A has two X, B has two Y; alpha=5.
    model = likelihood_from_counts(['x', 'y'], ['A', 'B'], Counter(x=2,y=2),
                                   {'A': Counter(x=2), 'B': Counter(y=2)}, {})
    assert model['matrix'][0] == pytest.approx([9/14, 5/14])
    assert model['matrix'][1] == pytest.approx([5/14, 9/14])
    assert model['matrix'][2] == [.5, .5]


def test_same_model_threshold_is_twenty_and_missing_part_uses_fleet_prior():
    fleet = Counter(x=30,y=30)
    all_part = {'A': Counter(x=20,y=20)}
    a = likelihood_from_counts(['x','y'], ['A', 'UNSEEN'], fleet, all_part, {'A': Counter(x=19)})
    assert a['scopes'][0]['scope'] == 'fleet'
    assert a['matrix'][0] == a['matrix'][1] == [.5, .5]
    b = likelihood_from_counts(['x','y'], ['A'], fleet, all_part, {'A': Counter(x=20)})
    assert b['scopes'][0]['scope'] == 'same_model'
    assert b['matrix'][0] == pytest.approx([.9, .1])


def test_not_sure_preserves_beliefs_and_unoffered_answer_is_rejected():
    book = load_codebook()
    prior = [.5,.5]
    model = {'values':['CL','CR'], 'matrix':[[.9,.1],[.1,.9]]}
    question = select_question(prior, {'stage_of_operation':model}, codebook=book)
    assert answer_question(prior, question, NOT_SURE) == prior
    assert answer_question(prior, question, 'CL') == pytest.approx([.9,.1])
    assert prior == [.5,.5]
    with pytest.raises(ValueError,match='offered'):
        answer_question(prior, question, 'invented')
    assert select_question(prior, {'stage_of_operation':model}, excluded=['stage_of_operation'], codebook=book) is None


def test_selection_maximizes_gain_ties_deterministically_and_random_is_seeded():
    models = {'stage_of_operation': {'values':['CL','CR'],'matrix':[[1,0],[0,1]]},
              'how_discovered': {'values':['V','C'],'matrix':[[.5,.5],[.5,.5]]}}
    q = select_question([.5,.5], models, codebook=load_codebook())
    assert q['attribute'] == 'stage_of_operation' and q['gain_bits'] == 1
    assert '1.000 of 1.000' in q['reason']
    assert q['options'][0]['label'] == 'CLIMB (CL)'
    a = select_question([.5,.5], models, codebook=load_codebook(), strategy='random', rng=random.Random(5))
    b = select_question([.5,.5], models, codebook=load_codebook(), strategy='random', rng=random.Random(5))
    assert a == b


def test_zero_probability_answer_and_degenerate_domain_are_not_invented():
    with pytest.raises(ValueError,match='zero probability'):
        posterior([1,0],[[1,0],[0,1]],1)
    assert select_question([1], {'stage_of_operation':{'values':['CL'],'matrix':[[1]]}},codebook=load_codebook()) is None


def test_attribute_extraction_preserves_raw_codes_and_honest_mention_semantics():
    s = schema()
    r = {'stage_of_operation':'CL','how_discovered':'V','nature_of_condition':'K','precautionary_procedure':'K',
         'part_condition':'cracked','part_location':'ZN 243 LEFT','text':'No leaks found. Vibration was reported after recent maintenance.'}
    values = read_attributes(r,s)
    assert values['stage_of_operation'] == 'CL' and values['part_condition'] == 'CRACKED'
    assert values['location_zone'] == '200'
    assert values['leak'] == 'mentioned'  # It does NOT claim the aircraft has a leak.
    assert values['noise_or_vibration'] == 'mentioned' and values['after_recent_maintenance'] == 'mentioned'
    assert values['smoke_or_odour'] == 'not_mentioned'
    assert read_attributes({},s)['location_zone'] == OTHER
    assert read_attributes({'stage_of_operation':'NEW_UNMAPPED'},s)['stage_of_operation'] == OTHER
    assert option_label('stage_of_operation','CL',load_codebook()) == 'CLIMB (CL)'


def test_vocabulary_is_fit_only_with_deterministic_top_thirty_and_no_guessing(tmp_path):
    with pytest.raises(ValueError,match='2023'):
        fit_schema([{'year':2024}],corpus_sha256='a'*64)
    records=[{'year':2023,'part_condition':f'C{i:02}'} for i in range(35)]
    s=fit_schema(records,corpus_sha256='a'*64)
    assert s['part_condition_top30'] == [f'C{i:02}' for i in range(30)]
    path=tmp_path/'missing.json'
    path.write_text('{}')
    with pytest.raises(ValueError,match='provenance'):
        load_codebook(path)
    assert set(CODED)|set(CUES)|{'part_condition','location_zone'} == set(s['domains'])


def test_record_likelihood_builder_selects_model_scope_and_normalizes_every_row():
    s=schema()
    records=[{'part_name':'PUMP','aircraft_model':'M1','stage_of_operation':'CL','part_condition':'CRACKED'} for _ in range(20)]
    records += [{'part_name':'PUMP','aircraft_model':'M2','stage_of_operation':'CR'} for _ in range(20)]
    models=build_likelihoods(records,['PUMP'],s,aircraft_model='M1')
    assert models['stage_of_operation']['scopes'][0] == {'part_name':'PUMP','scope':'same_model','n':20}
    for model in models.values():
        assert all(sum(row)==pytest.approx(1) for row in model['matrix'])
