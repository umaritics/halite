"""A human-selected point is reusable only with matching immutable evidence."""
from copy import deepcopy
import json
import shutil

import pytest

from investigation.experiments.frozen_policy import (
    AUDIT, POLICY, PROTOCOL, REPO, load_frozen_policy, preflight_held_out,
)


@pytest.fixture()
def frozen_repo(tmp_path):
    policy = json.loads((REPO/POLICY).read_text())
    for relative in [POLICY, PROTOCOL, *policy['frozen_files_sha256']]:
        destination = tmp_path/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(REPO/relative,destination)
    return tmp_path


def test_user_choice_matches_actual_selected_2024_row_and_managed_runtime_contract():
    from config import Settings
    from investigation.live_questions import QuestionController
    policy = load_frozen_policy()
    assert policy['user_decision'] == 'Freeze 0.80 answer / 0.50 gain (Recommended)'
    assert policy['parameters'] == {'tau_answer':.8,'g_min':.5,'n_min':2,'max_questions':3}
    assert policy['selected_2024_row']['n_answered'] == 23
    assert policy['selected_2024_row']['n_correct_top1'] == 16
    controller = QuestionController(policy)
    assert controller.parameters.tau_answer == .8 and controller.parameters.g_min == .5
    assert QuestionController.from_settings(Settings(_env_file=None,SESSION_QUESTIONS_ENABLED=False)) is None
    preflight = preflight_held_out()
    assert preflight['held_out_accessed'] is preflight['runtime_activated'] is False
    assert preflight['protocol']['year'] == 2025
    assert preflight['protocol']['sensitivity_label_cutoff'].startswith('2025-01-02')


@pytest.mark.parametrize('relative', ['backend/investigation/beliefs.py',
                                    'docs/fyp1-final/OPERATING_POINT_DECISION.md', AUDIT])
def test_frozen_method_decision_or_chronology_cannot_change_silently(frozen_repo, relative):
    path = frozen_repo/relative
    path.write_bytes(path.read_bytes()+b'\nchanged synthetic fixture\n')
    with pytest.raises(ValueError,match='Frozen research file changed'):
        preflight_held_out(frozen_repo)


@pytest.mark.parametrize('change,error', [('experimental','explicitly selected'),
                                        ('threshold','thresholds'), ('wording','relative-support'),
                                        ('evidence','two-record')])
def test_unaccepted_threshold_or_semantic_changes_fail(frozen_repo, change, error):
    path = frozen_repo/POLICY
    data = json.loads(path.read_text())
    if change == 'experimental':data['status'] = 'experimental'
    elif change == 'threshold':data['parameters']['tau_answer'] = .75
    elif change == 'wording':data['belief_label'] = 'probability'
    else:data['parameters']['n_min'] = 1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match=error):
        preflight_held_out(frozen_repo)


@pytest.mark.parametrize('field', ['selected_policy_sha256','stopping_policy_grid_allowed',
                                 'calibration_refit_allowed','probability_wording_allowed',
                                 'sensitivity_label_cutoff'])
def test_pretest_protocol_rejects_refit_sweep_or_shifted_availability(frozen_repo, field):
    path = frozen_repo/PROTOCOL
    data = json.loads(path.read_text())
    data[field] = True if field.endswith('allowed') else 'synthetic-changed-value'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        preflight_held_out(frozen_repo)


def test_preflight_preserves_every_recorded_artifact(frozen_repo):
    import hashlib
    paths = [p for p in frozen_repo.rglob('*') if p.is_file()]
    before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    original = preflight_held_out(frozen_repo)
    changed = deepcopy(original)
    changed['policy']['parameters']['tau_answer'] = .1
    assert preflight_held_out(frozen_repo) == original
    assert before == {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_pretest_protocol_keeps_all_metrics_and_abstention_off_comparison(frozen_repo):
    path = frozen_repo/PROTOCOL
    data = json.loads(path.read_text())
    data['required_metrics'].remove('named_top_ECE_10_equal_width_bins')
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='every declared metric'):
        preflight_held_out(frozen_repo)
