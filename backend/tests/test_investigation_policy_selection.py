"""Stopping behavior, exact cluster arithmetic and frozen-input integration."""
from copy import deepcopy
import json

import numpy as np
import pytest

from investigation.experiments.policy_selection import (
    ROOT, cluster_weights, load_inputs, metrics, run, score_outcome, stop_prefix, summarize,
)
from investigation.policy import PolicyParameters


def hypotheses(counts=(2, 2)):
    return [{'part_name': name, 'evidence_count': count} for name, count in zip(('A', 'B'), counts)]


def trace(first=(.6, .3, .1), second=(.02, .95, .03), gain=.125):
    return [{'beliefs': list(first), 'questions_asked': 0, 'attribute': None, 'gain_bits': None},
            {'beliefs': list(second), 'questions_asked': 1, 'attribute': 'part_condition',
             'gain_bits': gain, 'answer': 'SYNTHETIC'}]


def test_answer_precedes_question_and_cannot_use_a_future_better_posterior():
    stopped = stop_prefix(hypotheses(), trace(), PolicyParameters(.6, 0, max_questions=1))
    assert stopped['decision'] == 'answer'
    assert stopped['questions_asked'] == 0
    assert stopped['named_order'] == ['A', 'B']
    assert score_outcome(stopped, 'A') == [1, 1, 1, 1, 0, 0]
    assert score_outcome(stopped, 'B') == [1, 1, 0, 1, 0, 0]


def test_gain_boundary_and_evidence_count_follow_the_terminal_named_part():
    asked = stop_prefix(hypotheses(), trace(), PolicyParameters(.9, .125, max_questions=1))
    assert (asked['decision'], asked['questions_asked'], asked['named_order']) == ('answer', 1, ['B', 'A'])
    rejected = stop_prefix(hypotheses(), trace(), PolicyParameters(.9, .125001, max_questions=1))
    assert (rejected['decision'], rejected['questions_asked']) == ('abstain', 0)
    thin = stop_prefix(hypotheses((3, 1)), trace(), PolicyParameters(.9, 0, max_questions=1))
    assert (thin['decision'], thin['questions_asked']) == ('abstain', 1)
    assert thin['history'][-1]['evidence_count'] == 1


def test_prefix_matches_actual_managed_question_controller_at_each_step():
    from investigation.attributes import load_codebook
    from investigation.experiments.simulated_technician import simulate
    from investigation.live_questions import QuestionController, _with_posterior
    from investigation.questions import answer_question
    model = {'values': ['X', 'Y'], 'matrix': [[.99, .01], [.01, .99], [.5, .5]]}
    models = {'part_condition': model}
    book = load_codebook()
    saved = simulate([.45, .45, .1], models, {'part_condition': 'X'},
                     codebook=book, strategy='information_gain', query_id='synthetic')
    policy = {'status': 'experimental', 'selection_year': 2024, 'ranker_version': 'mid_heuristic-v1',
              'parameters': {'tau_answer': .8, 'g_min': .01, 'n_min': 2, 'max_questions': 3}}
    controller = QuestionController(policy)
    response = {'beliefs': {'hypotheses': [{**h, 'belief': .45} for h in hypotheses()],
                           'other': .1, 'calibrated': True}, 'case_state': {}}
    state = {'basis_names': ['A', 'B'], 'models': models, 'answers': [],
             'codebook': book, 'policy': policy}
    response = controller._choose(response, state)
    assert response['decision'] == 'ask'
    values = answer_question([.45, .45, .1], response['question'], 'X')
    response['beliefs'] = _with_posterior(response['beliefs'], ['A', 'B'], values)
    state['answers'].append({'attribute': 'part_condition', 'value': 'X'})
    response = controller._choose(response, state)
    stopped = stop_prefix(hypotheses(), saved, PolicyParameters(**policy['parameters']))
    assert response['decision'] == stopped['decision'] == 'answer'
    assert stopped['questions_asked'] == 1
    assert stopped['beliefs'] == values


def test_padding_and_empty_rankings_cannot_manufacture_questions_or_answers():
    empty = {'beliefs': [1], 'questions_asked': 0, 'attribute': None, 'gain_bits': None}
    stopped = stop_prefix([], [empty] * 4, PolicyParameters(0, 0))
    assert stopped['decision'] == 'abstain' and stopped['questions_asked'] == 0
    bad = trace()
    bad[1]['beliefs'] = [float('nan'), 0, 1]
    with pytest.raises(ValueError, match='finite'):
        stop_prefix(hypotheses(), bad, PolicyParameters(.99, 0, max_questions=1))
    with pytest.raises(ValueError, match='trace length'):
        stop_prefix(hypotheses(), bad, PolicyParameters(.99, 0))


def test_cluster_ratios_use_all_pairs_in_a_sampled_original_and_keep_null_accuracy():
    rows = [[1, 1, 1, 1, 0, 0], [1, 0, 0, 0, 3, 1], [1, 1, 0, 0, 1, 0]]
    weights = np.array([[2, 0], [0, 2], [1, 1]])
    result = summarize(rows, ['A', 'A', 'B'], weights=weights)
    assert result['n_originals'] == 2 and result['n_pairs'] == 3
    assert result['coverage'] == pytest.approx(2/3)
    assert result['accuracy_top1'] == .5 and result['accuracy_top3'] == .5
    assert result['unsupported_suggestion_rate'] == pytest.approx(1/3)
    assert result['mean_questions'] == pytest.approx(4/3)
    assert result['ci95']['coverage']['low'] == pytest.approx(.5083333333333333)
    assert result['ci95']['coverage']['high'] == pytest.approx(.9833333333333333)
    abstained = summarize([[1, 0, 0, 0, 2, 1]], ['A'], weights=np.ones((5, 1)))
    assert abstained['accuracy_top1'] is None
    assert abstained['ci95']['accuracy_top1'] == {'low': None, 'high': None, 'valid_resamples': 0}
    assert metrics([2, 0, 0, 0, 4, 2])['mean_questions'] == 2
    draws = cluster_weights(['A', 'B'], seed=9, resamples=10)
    assert np.all(draws.sum(axis=1) == 2)
    assert np.array_equal(draws, cluster_weights(['A', 'B'], seed=9, resamples=10))
    with pytest.raises(ValueError, match='positive bootstrap'):
        cluster_weights(['A'], seed=9, resamples=0)
    with pytest.raises(ValueError, match='inconsistent'):
        summarize(rows, ['A'], weights=weights)


def test_exact_frozen_2024_inputs_and_small_grid_export_are_verified(tmp_path):
    protocol, cohorts = load_inputs()
    assert set(cohorts) == {'all_attributes', 'structured_fields_only', 'coded_fields_only'}
    assert all(len(rows) == 389 for rows in cohorts.values())
    small = deepcopy(protocol)
    small.update(tau_answer_grid=[0, 1], g_min_grid=[0, .5], bootstrap_resamples=5)
    output = tmp_path / 'synthetic-small-grid-verification'
    result = run(output, protocol=small)
    assert len(result['tables']) == 3 * 4 * 3 * 4
    assert result['selected_operating_point'] is None and not result['held_out_evaluated']
    assert json.loads((output/'selection.json').read_text()) == result
    assert (output/'selection.csv').read_text().startswith('cohort,stratum,strategy,')
    assert all(row['n_pairs'] == 389 for row in result['tables'] if row['stratum'] == 'all')
    with pytest.raises(FileExistsError, match='Preserve'):
        run(output, protocol=small)
    bad = deepcopy(protocol); bad['year'] = 2025
    with pytest.raises(ValueError, match='2024 traces only'):
        load_inputs(protocol=bad)
    bad = deepcopy(protocol)
    path = next(iter(bad['input_sha256']))
    bad['input_sha256'][path] = '0' * 64
    with pytest.raises(ValueError, match='fingerprint mismatch'):
        load_inputs(protocol=bad)
