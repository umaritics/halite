"""Read only checksum-pinned published experiments; never generate substitute data."""
import hashlib
import json
import math
from pathlib import Path
from investigation.experiments.frozen_policy import POLICY, PROTOCOL
from investigation.policy import PolicyParameters

ROOT = Path(__file__).parent / 'experiments/results'
FILES = {
    'question_selection': 'question_selection_2024_v2/results.json',
    'decision_selection': 'decision_selection_2024_v2/selection.json',
    'stopping_selection': 'policy_selection_2024_v1/selection.json',
    'held_out': 'held_out_2025_v1/results.json',
    'held_out_verification': 'held_out_2025_v1/verification.json',
}
GROUPS = ('all_attributes', 'structured_fields_only', 'coded_fields_only')
POLICIES = ('information_gain', 'random', 'no_questions')


class ResultsUnavailable(ValueError):
    """Missing, altered or incompatible published evidence."""


def number(value, *, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ResultsUnavailable('Expected a finite measurement.')
    if (low is not None and value < low) or (high is not None and value > high):
        raise ResultsUnavailable('Measurement outside its declared range.')


def interval(value, *, probability=False):
    number(value['low'], low=0 if probability else None, high=1 if probability else None)
    number(value['high'], low=0 if probability else None, high=1 if probability else None)
    if value['low'] > value['high']:
        raise ResultsUnavailable('Reversed confidence interval.')
    if type(value['valid_resamples']) is not int or value['valid_resamples'] <= 0:
        raise ResultsUnavailable('Missing valid bootstrap resamples.')


def question_cohort(cohort):
    if type(cohort['n_pairs']) is not int or type(cohort['n_originals']) is not int or not 0 < cohort['n_originals'] <= cohort['n_pairs']:
        raise ResultsUnavailable('Invalid sample size.')
    if set(cohort['policies']) != set(POLICIES):
        raise ResultsUnavailable('The three declared controls are required.')
    for rows in cohort['policies'].values():
        if [r['after_questions'] for r in rows] != [0, 1, 2, 3]:
            raise ResultsUnavailable('Question budgets must remain complete and ordered.')
        for row in rows:
            for metric in ('top1', 'top3', 'entropy'):
                number(row[metric], low=0, high=None if metric == 'entropy' else 1)
                interval(row['ci95'][metric], probability=metric != 'entropy')
    differences = cohort['information_gain_minus_random']
    if [r['after_questions'] for r in differences] != [0, 1, 2, 3]:
        raise ResultsUnavailable('Paired differences are incomplete.')
    for row in differences:
        for metric in ('top1', 'top3', 'entropy'):
            number(row[metric])
            interval(row['ci95'][metric])


def validate(question, decision):
    if question['method_version'] != 'question-selection-v2' or decision['method_version'] != 'mid-beliefs-selection-v2':
        raise ResultsUnavailable('Unrecognized method versions.')
    if question['year'] != 2024 or decision['split'] != {'fit': [2023], 'select': [2024], 'test': [2025]}:
        raise ResultsUnavailable('Unexpected fit/selection split.')
    if question['held_out_evaluated'] is not False or decision['held_out_evaluated'] is not False:
        raise ResultsUnavailable('This publication is selection evidence, not held-out evidence.')
    if question['parameters']['fit_years'] != [2023] or question['ranker_version'] != decision['ranker_version']:
        raise ResultsUnavailable('Incompatible fit/ranker provenance.')
    if question['corpus']['corpus_sha256'] != decision['selection_corpus']['corpus_sha256']:
        raise ResultsUnavailable('Experiments do not share the frozen corpus.')
    if set(question['summaries']) != set(GROUPS):
        raise ResultsUnavailable('All declared attribute controls are required.')
    for group in question['summaries'].values():
        question_cohort(group['all'])
        for cohort in group['by_part_change'].values():
            question_cohort(cohort)
    selection = decision['selection']
    if selection['n'] != question['summaries']['all_attributes']['all']['n_pairs']:
        raise ResultsUnavailable('Sample counts disagree.')
    if selection['selected_operating_point'] is not None:
        raise ResultsUnavailable('Accepted policy publication needs its separate decision evidence.')
    rows = selection['curve']
    if not rows:
        raise ResultsUnavailable('Missing accuracy–coverage curve.')
    for row in [*rows, selection['abstention_off']]:
        if type(row['n_cases']) is not int or row['n_cases'] != selection['n'] or type(row['n_answered']) is not int or not 0 <= row['n_answered'] <= row['n_cases']:
            raise ResultsUnavailable('Curve denominators disagree.')
        if abs(row['coverage'] - row['n_answered'] / row['n_cases']) > 1e-10:
            raise ResultsUnavailable('Coverage does not match the saved denominator.')
        for metric in ('coverage', 'accuracy_top1', 'accuracy_top3', 'unsupported_suggestion_rate'):
            if row[metric] is None:
                if metric not in ('accuracy_top1', 'accuracy_top3') or row['n_answered']:
                    raise ResultsUnavailable('Unexpected missing metric.')
            else:
                number(row[metric], low=0, high=1)
                interval(row['ci95'][metric], probability=True)
    thresholds = [r['tau_answer'] for r in rows]
    if thresholds != sorted(set(thresholds)):
        raise ResultsUnavailable('Threshold rows must be unique and ordered.')
    for value in thresholds:
        number(value, low=0, high=1)


def stopping_metrics(row):
    n, answered = row['n_pairs'], row['n_answered']
    counts = [n, row['n_originals'], answered, row['n_correct_top1'], row['n_correct_top3']]
    if any(type(v) is not int for v in counts) or not 0 < counts[1] <= n or not 0 <= counts[3] <= counts[4] <= answered <= n:
        raise ResultsUnavailable('Invalid stopping denominators.')
    expected = {'coverage': answered/n, 'abstention_rate': 1-answered/n,
                'unsupported_suggestion_rate': (answered-row['n_correct_top3'])/n,
                'accuracy_top1': row['n_correct_top1']/answered if answered else None,
                'accuracy_top3': row['n_correct_top3']/answered if answered else None}
    for key in (*expected, 'mean_questions'):
        value = row[key]
        ci = row['ci95'][key]
        if key in expected:
            target = expected[key]
            if (value is None) != (target is None) or (value is not None and abs(value-target)>1e-10):
                raise ResultsUnavailable('Stopping metric disagrees with its denominator.')
        if value is None:
            if ci != {'low':None,'high':None,'valid_resamples':0}:
                raise ResultsUnavailable('Undefined answered accuracy needs an empty interval.')
        else:
            number(value,low=0,high=3 if key=='mean_questions' else 1)
            interval(ci,probability=key!='mean_questions')
            if ci['valid_resamples']>1000:
                raise ResultsUnavailable('Unexpected bootstrap count.')


def publication_freeze(backend_root=None):
    """Verify packaged backend inputs; full doc/source preflight remains in CI.

    Backend Docker images contain /app, not the repository's docs directory.
    Do not weaken the original pre-access checker or invent a repository mount.
    """
    backend_root = Path(backend_root) if backend_root is not None else Path(__file__).resolve().parents[1]
    policy_path = backend_root/POLICY.removeprefix('backend/')
    policy = json.loads(policy_path.read_bytes())
    if (policy['status']!='selected' or policy['selection_year']!=2024 or policy['belief_label']!='relative support' or
        policy['held_out_evaluated_at_freeze'] is not False):
        raise ResultsUnavailable('A recorded pre-test research choice is required.')
    parameters = PolicyParameters(**policy['parameters'])
    if parameters.n_min!=2 or parameters.max_questions!=3:
        raise ResultsUnavailable('Preserve the frozen evidence and question budgets.')
    for relative, expected in policy['frozen_files_sha256'].items():
        if relative.startswith('backend/'):
            path = (backend_root/relative.removeprefix('backend/')).resolve()
            if not path.is_relative_to(backend_root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise ResultsUnavailable('A packaged frozen research input changed.')
    policy['file_sha256'] = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    protocol_path = backend_root/PROTOCOL.removeprefix('backend/')
    protocol = json.loads(protocol_path.read_bytes())
    if protocol['selected_policy_sha256']!=policy['file_sha256']:
        raise ResultsUnavailable('Packaged protocol does not match the selected policy.')
    return {'policy':policy,'protocol':protocol,'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest()}


def validate_completed(contents, entries):
    proof = publication_freeze()
    policy = proof['policy']
    selected = contents['stopping_selection']
    held = contents['held_out']
    verification = contents['held_out_verification']
    fingerprints = {e['id']:e['sha256'] for e in entries}
    if (fingerprints['stopping_selection'] != policy['selection_sha256'] or
        selected['method_version'] != 'question-conditioned-selection-v1' or
        selected['held_out_evaluated'] is not False or policy['selected_2024_row'] not in selected['tables']):
        raise ResultsUnavailable('Selection must match the frozen accepted decision.')
    if (held['method_version']!='fixed-held-out-2025-v1' or held['year']!=2025 or
        held['held_out_evaluated'] is not True or held['selection_or_tuning_performed'] is not False or
        held['policy']!=policy or held['protocol']!=proof['protocol']):
        raise ResultsUnavailable('Held-out evidence does not match the pre-test freeze.')
    receipt = held['pretest_receipt']
    if (receipt['policy_sha256']!=policy['file_sha256'] or receipt['protocol_sha256']!=proof['protocol_sha256'] or
        receipt['parameters']!=policy['parameters']):
        raise ResultsUnavailable('Missing matching pre-access receipt.')
    if (verification['independent_held_out_point_metrics']!='PASS' or
        verification['all_question_and_stopping_intervals_replayed']!='PASS' or
        verification['held_out_tuning'] is not False or verification['policy_sha256']!=policy['file_sha256'] or
        verification['results_sha256']!=fingerprints['held_out'] or verification['case_counts']!=held['case_counts']):
        raise ResultsUnavailable('Held-out verifier receipt is incompatible.')
    signatures = set()
    for table in held['stopping']:
        signature = (table['cohort'],table['availability'],table['stratum'],table['strategy'])
        if signature in signatures:
            raise ResultsUnavailable('Duplicate held-out comparison.')
        signatures.add(signature)
        for key in ('chosen','abstention_off'):
            stopping_metrics(table[key])
        chosen, off = table['chosen'],table['abstention_off']
        if (chosen['n_pairs']!=off['n_pairs'] or chosen['n_originals']!=off['n_originals'] or
            chosen['mean_questions']!=off['mean_questions'] or chosen['ci95']['mean_questions']!=off['ci95']['mean_questions']):
            raise ResultsUnavailable('Abstention-off must preserve question burden and samples.')
        cohort = held['question_budget_summaries'][table['cohort']][table['availability']+'/'+table['stratum']]
        question_cohort(cohort)
        if cohort['n_pairs']!=chosen['n_pairs'] or cohort['n_originals']!=chosen['n_originals']:
            raise ResultsUnavailable('Question and stopping samples disagree.')
        ece = table['named_top_ece']
        number(ece['value'],low=0,high=1);interval(ece['ci95'],probability=True)
        bins = ece['bins']
        if [b['bin'] for b in bins]!=list(range(10)) or sum(b['n'] for b in bins)!=chosen['n_pairs']:
            raise ResultsUnavailable('Incomplete calibration bins.')
        for b in bins:
            if type(b['n']) is not int or type(b['correct_top1']) is not int or not 0 <= b['correct_top1'] <= b['n']:
                raise ResultsUnavailable('Invalid calibration bin counts.')
            number(b['support_sum'],low=0,high=b['n'])
        if abs(sum(abs(b['support_sum']-b['correct_top1']) for b in bins)/chosen['n_pairs']-ece['value'])>1e-10:
            raise ResultsUnavailable('Calibration bins disagree with ECE.')
    required = {(pool,availability,stratum,strategy) for pool in GROUPS
                for availability in ('primary_all','after_selection_labels')
                for stratum in ('all','same','named_to_named','unknown_to_named') for strategy in POLICIES}
    if signatures!=required or verification['tables_verified']!=len(required):
        raise ResultsUnavailable('All declared held-out controls and strata are required.')
    for pool in GROUPS:
        n = held['case_counts']['n_pairs']
        if held['question_budget_summaries'][pool]['primary_all/all']['n_pairs']!=n:
            raise ResultsUnavailable('Primary held-out counts disagree.')
    # Keep the full source checksum/provenance, send only the accepted gain slice.
    # This is a projection of saved rows, never a new sweep or calculation.
    return policy, {**selected,'tables':[r for r in selected['tables'] if r['g_min']==policy['parameters']['g_min']]}


def load_results(root=None):
    root = Path(root) if root is not None else ROOT
    try:
        manifest = root / 'publication.json'
        if manifest.stat().st_size > 16384:
            raise ResultsUnavailable('Publication manifest is too large.')
        raw_manifest = manifest.read_bytes()
        publication = json.loads(raw_manifest)
        if publication['schema_version'] != 'investigation-publication-v2':
            raise ResultsUnavailable('Unknown publication version.')
        entries = publication['artifacts']
        if entries == []:
            return {'schema_version': 'investigation-results-v2', 'state': 'empty', 'artifacts': []}
        if len(entries) != len(FILES) or {r['id'] for r in entries} != set(FILES):
            raise ResultsUnavailable('Publication artifacts are incomplete or duplicated.')
        contents = {}
        for entry in entries:
            relative = FILES[entry['id']]
            if entry['path'] != relative:
                raise ResultsUnavailable('Only the fixed published artifact paths are allowed.')
            path = root / relative
            if not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size > 8 * 1024 * 1024:
                raise ResultsUnavailable('Artifact path or size is invalid.')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ResultsUnavailable('Published experiment checksum changed.')
            contents[entry['id']] = json.loads(raw)
        validate(contents['question_selection'], contents['decision_selection'])
        policy, selection = validate_completed(contents,entries)
        contents['stopping_selection'] = selection
        return {'schema_version': 'investigation-results-v2', 'state': 'available',
                'publication_sha256': hashlib.sha256(raw_manifest).hexdigest(),
                'artifacts': entries, 'selected_policy':policy, **contents}
    except ResultsUnavailable:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError) as exc:
        raise ResultsUnavailable('Published experiment cannot be verified.') from exc
