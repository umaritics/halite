"""Read only checksum-pinned published experiments; never generate substitute data."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent / 'experiments/results'
FILES = {
    'question_selection': 'question_selection_2024_v2/results.json',
    'decision_selection': 'decision_selection_2024_v2/selection.json',
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


def load_results(root=None):
    root = Path(root) if root is not None else ROOT
    try:
        manifest = root / 'publication.json'
        if manifest.stat().st_size > 16384:
            raise ResultsUnavailable('Publication manifest is too large.')
        raw_manifest = manifest.read_bytes()
        publication = json.loads(raw_manifest)
        if publication['schema_version'] != 'investigation-publication-v1':
            raise ResultsUnavailable('Unknown publication version.')
        entries = publication['artifacts']
        if entries == []:
            return {'schema_version': 'investigation-results-v1', 'state': 'empty', 'artifacts': []}
        if len(entries) != len(FILES) or {r['id'] for r in entries} != set(FILES):
            raise ResultsUnavailable('Publication artifacts are incomplete or duplicated.')
        contents = {}
        for entry in entries:
            relative = FILES[entry['id']]
            if entry['path'] != relative:
                raise ResultsUnavailable('Only the fixed published artifact paths are allowed.')
            path = root / relative
            if not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size > 2 * 1024 * 1024:
                raise ResultsUnavailable('Artifact path or size is invalid.')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ResultsUnavailable('Published experiment checksum changed.')
            contents[entry['id']] = json.loads(raw)
        validate(contents['question_selection'], contents['decision_selection'])
        return {'schema_version': 'investigation-results-v1', 'state': 'available',
                'publication_sha256': hashlib.sha256(raw_manifest).hexdigest(),
                'artifacts': entries, **contents}
    except ResultsUnavailable:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError) as exc:
        raise ResultsUnavailable('Published experiment cannot be verified.') from exc
