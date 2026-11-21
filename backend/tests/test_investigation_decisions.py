"""Decision maths are tested against hand-computed values, not matching implementation loops."""
import json
import math
from types import SimpleNamespace

import pytest

from investigation.beliefs import BeliefParameters, entropy, load_parameters, score_beliefs
from investigation.policy import PolicyParameters, decide
from investigation import ranker_port
from investigation.experiments.calibration import fit_parameters, negative_log_likelihood
from investigation.experiments.abstention_curve import abstention_curve, evaluate_cases, expected_calibration_error

VERSION = 'mid_heuristic-v1'
SHA = 'a' * 64


def hypotheses(*scores):
    return [{'part_name': f'PART {i}', 'score': score, 'evidence_count': 2} for i, score in enumerate(scores)]


def parameters(t=1, c=0):
    return BeliefParameters(VERSION, t, c, (2023,), SHA)


def test_hand_computed_softmax_other_and_entropy():
    # exp(log(2))=2, exp(0)=1, other=1. Distribution .5,.25,.25, H=1.5 bits.
    source = hypotheses(math.log(2), 0)
    result = score_beliefs(source, ranker_version=VERSION, parameters=parameters())
    assert [h['belief'] for h in result['hypotheses']] == pytest.approx([.5, .25])
    assert result['other'] == pytest.approx(.25)
    assert result['entropy'] == pytest.approx(1.5)
    assert result['calibrated'] and result['label'] == 'relative support'
    assert 'belief' not in source[0]


def test_empty_and_single_candidate_never_force_certainty():
    empty = score_beliefs([], ranker_version=VERSION)
    assert empty['other'] == 1 and empty['entropy'] == 0
    single = score_beliefs(hypotheses(900), ranker_version=VERSION)
    assert single['hypotheses'][0]['belief'] == single['other'] == .5
    assert not single['calibrated'] and single['parameters'] is None


def test_extreme_finite_scores_stay_normalized():
    result = score_beliefs(hypotheses(1e308, -1e308), ranker_version=VERSION, parameters=parameters(1e-300))
    assert result['hypotheses'][0]['belief'] == 1
    assert result['entropy'] == 0


def test_top_ten_only_and_version_mismatch():
    result = score_beliefs(hypotheses(*range(20)), ranker_version=VERSION)
    assert len(result['hypotheses']) == 10
    assert sum(h['belief'] for h in result['hypotheses']) + result['other'] == pytest.approx(1)
    with pytest.raises(ValueError, match='different ranker'):
        score_beliefs([], ranker_version='v2', parameters=parameters())


@pytest.mark.parametrize('scores', [[float('nan')], [float('inf')]])
def test_nonfinite_score_rejected(scores):
    with pytest.raises(ValueError):
        score_beliefs(hypotheses(*scores), ranker_version=VERSION)


def test_duplicate_parts_and_bad_entropy_are_rejected():
    with pytest.raises(ValueError):
        score_beliefs(hypotheses(1) * 2, ranker_version=VERSION)
    for values in ([.2, .2], [-1, 2], [float('nan')]):
        with pytest.raises(ValueError):
            entropy(values)


def test_parameter_file_requires_version_and_fit_provenance(tmp_path):
    path = tmp_path / 'params.json'
    path.write_text(json.dumps(parameters().as_dict()))
    assert load_parameters(path, ranker_version=VERSION) == parameters()
    with pytest.raises(ValueError):
        load_parameters(path, ranker_version='v2')
    for years in ((2024,), (2025,), ()):
        with pytest.raises(ValueError):
            BeliefParameters(VERSION, 1, 0, years, SHA)
    with pytest.raises(ValueError):
        BeliefParameters(VERSION, 0, 0, (2023,), SHA)


def test_rule_boundaries_answer_ask_abstain_and_report():
    beliefs = {'hypotheses': [{'belief': .8, 'evidence_count': 2}], 'other': .2, 'calibrated': True}
    config = PolicyParameters(.8, .4)
    question = {'attribute': 'test', 'gain_bits': .4}
    assert decide(beliefs, parameters=config, best_question=question)['decision'] == 'answer'
    beliefs['hypotheses'][0]['evidence_count'] = 1
    result = decide(beliefs, parameters=config, best_question=question, questions_asked=2)
    assert result['decision'] == 'ask' and result['question'] == question
    assert result['policy_inputs']['parameters']['tau_answer'] == .8
    assert decide(beliefs, parameters=config, best_question=question, questions_asked=3)['decision'] == 'abstain'
    assert decide(beliefs, parameters=config)['decision'] == 'abstain'
    assert decide(beliefs)['policy_status'] == 'not_configured'
    assert decide(beliefs, report_mode=True)['decision'] == 'report'
    question['gain_bits'] = .3999
    assert decide(beliefs, parameters=config, best_question=question)['decision'] == 'abstain'


@pytest.mark.parametrize('kwargs', [{'tau_answer': -1, 'g_min': 0}, {'tau_answer': .5, 'g_min': float('nan')},
                                   {'tau_answer': .5, 'g_min': 0, 'max_questions': -1},
                                   {'tau_answer': .5, 'g_min': 0, 'n_min': True}])
def test_invalid_policy_configuration(kwargs):
    with pytest.raises(ValueError):
        PolicyParameters(**kwargs)


def test_missing_questions_never_manufactures_ask():
    result = decide({'hypotheses': [], 'other': 1}, parameters=PolicyParameters(0, 0))
    assert result['decision'] == 'abstain' and result['question'] is None
    with pytest.raises(ValueError):
        decide({'hypotheses': []}, questions_asked=-1)


def test_ranker_port_preserves_legacy_and_reports_fallback(graph_repo, monkeypatch):
    state = {'symptoms': ['hydraulic pressure'], 'observations': [], 'ruled_out': []}
    expected_context = ranker_port.legacy.build_copilot_context(graph_repo, None, state)
    expected = ranker_port.legacy.rank_copilot_checks(expected_context, [])[:10]
    result = ranker_port.rank(graph_repo, symptoms=state['symptoms'])
    assert result['hypotheses'] == expected
    assert result['ranker_version'] == VERSION
    def missing(_):
        raise ModuleNotFoundError(name='retrieval')
    monkeypatch.setattr(ranker_port, 'import_module', missing)
    result = ranker_port.rank(graph_repo, symptoms=state['symptoms'], mode='dense')
    assert result['mode'] == 'mid_heuristic' and result['warnings']
    with pytest.raises(ValueError, match='prefiltered'):
        ranker_port.rank(graph_repo, symptoms=[], as_of='2023-01-01')


def test_new_ranker_delegation_and_broken_import_do_not_silently_fallback(graph_repo, monkeypatch):
    calls = []
    expected = {'mode': 'dense', 'ranker_version': 'v2', 'hypotheses': [], 'evidence': []}
    def rank(*args, **kwargs):
        calls.append(kwargs)
        return expected
    monkeypatch.setattr(ranker_port, 'import_module', lambda _: SimpleNamespace(rank=rank))
    assert ranker_port.rank(graph_repo, symptoms=['x'], mode='dense', as_of='date') == expected
    assert calls[0]['as_of'] == 'date'
    def broken(_):
        raise ModuleNotFoundError(name='missing_installed_dependency')
    monkeypatch.setattr(ranker_port, 'import_module', broken)
    with pytest.raises(ModuleNotFoundError):
        ranker_port.rank(graph_repo, mode='dense')


def cases():
    return [{'case_id': str(i), 'year': 2023, 'ranker_version': VERSION,
             'hypotheses': hypotheses(3, 0), 'answer_part': 'PART 0' if i < 8 else 'ABSENT'} for i in range(10)]


def test_fit_reduces_nll_and_refuses_selection_test_or_mixed_versions():
    source = cases()
    fit = fit_parameters(source, ranker_version=VERSION, corpus_sha256=SHA)
    p = fit['parameters']
    assert fit['mean_nll'] < negative_log_likelihood(source, 1, 0)
    assert fit['mean_nll'] == pytest.approx(negative_log_likelihood(source, p['temperature'], p['other_score']))
    for field, value in [('year', 2024), ('year', 2025), ('ranker_version', 'another')]:
        broken = [dict(source[0], **{field: value})]
        with pytest.raises(ValueError):
            fit_parameters(broken, ranker_version=VERSION, corpus_sha256=SHA)


def test_nll_other_bucket_is_hand_computed_and_stable():
    case = {'hypotheses': hypotheses(math.log(2), 0), 'answer_part': 'NOT RETRIEVED'}
    assert negative_log_likelihood([case], 1, 0) == pytest.approx(math.log(4))
    assert math.isfinite(negative_log_likelihood([{'hypotheses': hypotheses(1000, 0), 'answer_part': 'PART 1'}], .01, 0))


def test_accuracy_coverage_denominators_empty_answers_bootstrap_and_ece():
    source = cases()
    rows = evaluate_cases(source, ranker_version=VERSION, parameters=parameters(1, 0))
    # top confidence exp(3)/(exp(3)+2), correctness 8/10: ECE=abs(confidence-.8).
    assert expected_calibration_error(rows) == pytest.approx(abs(math.exp(3) / (math.exp(3) + 2) - .8))
    curve = abstention_curve(rows, thresholds=[0, .99], resamples=40)
    assert curve == abstention_curve(rows, thresholds=[0, .99], resamples=40)
    a, b = curve['curve']
    assert a['coverage'] == 1 and a['accuracy_top1'] == .8
    assert a['unsupported_suggestion_rate'] == .2
    assert b['coverage'] == 0 and b['accuracy_top1'] is None
    assert b['ci95']['accuracy_top1']['valid_resamples'] == 0
    assert curve['selected_operating_point'] is None
    assert all(x['ci95']['coverage']['valid_resamples'] == 40 for x in curve['curve'])


def test_baseline_turns_off_both_confidence_and_evidence_gates():
    source = cases()[:1]
    source[0]['hypotheses'][0]['evidence_count'] = 1
    rows = evaluate_cases(source, ranker_version=VERSION, parameters=None)
    curve = abstention_curve(rows, thresholds=[0], resamples=10)
    assert curve['curve'][0]['coverage'] == 0
    assert curve['abstention_off']['coverage'] == 1


def test_bootstrap_retains_dependence_of_pairs_sharing_an_original():
    source = cases()[:2]
    for c in source:
        c['query_id'] = 'same-original'
    source[0]['answer_part'] = 'PART 0'
    source[1]['answer_part'] = 'ABSENT'
    rows = evaluate_cases(source, ranker_version=VERSION, parameters=parameters())
    result = abstention_curve(rows, thresholds=[0], resamples=20)
    assert result['n_original_reports'] == 1
    assert result['curve'][0]['ci95']['accuracy_top1']['low'] == .5
    assert result['curve'][0]['ci95']['accuracy_top1']['high'] == .5
