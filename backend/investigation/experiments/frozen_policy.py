"""Validate Usman's recorded choice and frozen inputs before held-out access."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from investigation.policy import PolicyParameters

REPO = Path(__file__).resolve().parents[3]
POLICY = 'backend/investigation/params/selected-policy-v1.json'
PROTOCOL = 'backend/investigation/experiments/held_out_protocol_v1.json'
AUDIT = 'docs/work/usman/evidence/phase16-frozen-policy/label-availability-audit.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frozen_policy(repo=REPO):
    repo = Path(repo).resolve()
    path = repo/POLICY
    policy = json.loads(path.read_text())
    if (policy.get('version') != 'selected-research-policy-v1' or
        policy.get('status') != 'selected' or policy.get('selection_year') != 2024 or
        policy.get('held_out_evaluated_at_freeze') is not False):
        raise ValueError('An explicitly selected, pre-held-out 2024 policy is required.')
    parameters = PolicyParameters(**policy['parameters'])
    if parameters.n_min != 2 or parameters.max_questions != 3:
        raise ValueError('Preserve the two-record / three-question contract.')
    if policy.get('belief_label') != 'relative support' or not policy.get('user_decision'):
        raise ValueError('Recorded user decision and relative-support wording are required.')
    if policy.get('attribute_pool') != 'all_attributes' or policy.get('strategy') != 'information_gain':
        raise ValueError('This choice applies to the all-attribute information-gain policy.')
    frozen = policy['frozen_files_sha256']
    required = {policy['decision_reference'], AUDIT,
                'backend/investigation/params/mid_heuristic-v1.json',
                'backend/investigation/params/report-attributes-v1.json',
                'backend/investigation/data/faa_codes.json',
                'backend/investigation/experiments/results/policy_selection_2024_v1/selection.json'}
    required.update('backend/investigation/' + name for name in (
        'beliefs.py','policy.py','questions.py','attributes.py','ranker_port.py',
        'experiments/offline.py','experiments/temporal_questions.py',
        'experiments/simulated_technician.py','experiments/policy_selection.py',
        'experiments/abstention_curve.py'))
    required.add('backend/services/diagnostic_retrieval.py')
    if not required.issubset(frozen):
        raise ValueError('The decision, fit, schema, codebook and selection must all be frozen.')
    for relative, expected in frozen.items():
        file = (repo/relative).resolve()
        if not file.is_relative_to(repo) or sha(file) != expected:
            raise ValueError('Frozen research file changed: ' + relative)
    selection_path = repo/'backend/investigation/experiments/results/policy_selection_2024_v1/selection.json'
    if sha(selection_path) != policy['selection_sha256']:
        raise ValueError('The chosen point must identify the exact verified selection artifact.')
    selection = json.loads(selection_path.read_text())
    row = policy['selected_2024_row']
    if (row not in selection['tables'] or row['cohort'] != policy['attribute_pool'] or
        row['strategy'] != policy['strategy'] or row['stratum'] != 'all' or
        row['tau_answer'] != parameters.tau_answer or row['g_min'] != parameters.g_min):
        raise ValueError('Accepted thresholds and verified 2024 row disagree.')
    fit = json.loads((repo/'backend/investigation/params/mid_heuristic-v1.json').read_text())
    schema = json.loads((repo/'backend/investigation/params/report-attributes-v1.json').read_text())
    if (fit['ranker_version'] != policy['ranker_version'] or fit['fit_years'] != [2023] or
        schema['fit_years'] != [2023] or schema['corpus_sha256'] != fit['corpus_sha256']):
        raise ValueError('Preserve the same ranker and 2023 belief/attribute fit corpus.')
    result = deepcopy(policy)
    result['file_sha256'] = sha(path)
    return result


def preflight_held_out(repo=REPO):
    """Reads frozen artifacts only. Never downloads, inspects or scores 2025."""
    repo = Path(repo).resolve()
    policy = load_frozen_policy(repo)
    protocol = json.loads((repo/PROTOCOL).read_text())
    if protocol.get('selected_policy_sha256') != policy['file_sha256']:
        raise ValueError('The pre-test protocol does not match the frozen policy fingerprint.')
    if (protocol.get('version') != 'held-out-2025-v1' or
        protocol.get('status') != 'frozen-before-2025-access' or protocol.get('year') != 2025 or
        protocol.get('fit_years') != [2023] or protocol.get('selection_years') != [2024]):
        raise ValueError('Expected the fixed 2023 / 2024 / 2025 evaluation protocol.')
    for flag in ('stopping_policy_grid_allowed', 'calibration_refit_allowed', 'probability_wording_allowed'):
        if protocol.get(flag) is not False:
            raise ValueError('Held-out evaluation must not enable tuning or probability wording.')
    if (protocol['strategies'] != ['information_gain','random','no_questions'] or
        protocol['attribute_pools'] != ['all_attributes','structured_fields_only','coded_fields_only'] or
        protocol['question_budgets'] != [0,1,2,3] or protocol['bootstrap_resamples'] != 1000):
        raise ValueError('Preserve all controls, question budgets and 1000 cluster draws.')
    required_metrics = {'top1','top3','entropy_bits','coverage','answered_top1','answered_top3',
                        'unsupported_top3_outcome_key_rate','questions_per_case',
                        'named_top_ECE_10_equal_width_bins'}
    if set(protocol.get('required_metrics', [])) != required_metrics or protocol.get('rq4_comparators') != [
        'chosen stopping policy','answer every nonempty terminal ranking without confidence/evidence gates']:
        raise ValueError('Preserve every declared metric and the abstention-off comparator.')
    audit = json.loads((repo/AUDIT).read_text())
    cutoff = protocol['sensitivity_label_cutoff']
    if cutoff != audit['splits']['selection']['latest_answer_submission']:
        raise ValueError('The label-availability sensitivity cutoff changed.')
    if datetime.fromisoformat(cutoff).utcoffset() is None:
        raise ValueError('Label availability needs an explicit timezone.')
    return {'policy':policy, 'protocol':protocol, 'protocol_sha256':sha(repo/PROTOCOL),
            'held_out_accessed':False, 'runtime_activated':False}


if __name__ == '__main__':
    proof = preflight_held_out()
    print(json.dumps({'preflight':'PASS', 'parameters':proof['policy']['parameters'],
                      'policy_sha256':proof['policy']['file_sha256'],
                      'protocol_sha256':proof['protocol_sha256'],
                      'held_out_accessed':False, 'runtime_activated':False},indent=2))
