"""Pure Bayesian question maths and Dirichlet-smoothed report likelihoods."""
from __future__ import annotations

from collections import Counter
import math

from investigation.attributes import NOT_SURE, option_label, question_text, read_attributes
from investigation.beliefs import entropy


def _validate(prior, matrix):
    entropy(prior)
    if len(matrix) != len(prior) or not matrix or not matrix[0]:
        raise ValueError('Likelihood matrix must have one nonempty row per belief bucket.')
    width = len(matrix[0])
    for row in matrix:
        if len(row) != width or any(not math.isfinite(p) or p < 0 or p > 1 for p in row) or not math.isclose(sum(row), 1, abs_tol=1e-9):
            raise ValueError('Every likelihood row must be a normalized finite distribution.')


def posterior(prior, matrix, value_index):
    _validate(prior, matrix)
    if type(value_index) is not int or not 0 <= value_index < len(matrix[0]):
        raise ValueError('Answer index is outside the offered domain.')
    joint = [p * row[value_index] for p, row in zip(prior, matrix)]
    evidence = sum(joint)
    if evidence <= 0:
        raise ValueError('Answer has zero probability under the saved question model.')
    return [p / evidence for p in joint]


def expected_information_gain(prior, matrix):
    _validate(prior, matrix)
    before = entropy(prior)
    expected = 0.0
    for index in range(len(matrix[0])):
        marginal = sum(p * row[index] for p, row in zip(prior, matrix))
        if marginal > 0:
            expected += marginal * entropy(posterior(prior, matrix, index))
    gain = before - expected
    if gain < -1e-9:
        raise ValueError('Information gain cannot be negative.')
    return max(0.0, gain)


def build_likelihoods(records, hypothesis_names, schema, *, aircraft_model=None, alpha=5):
    """Caller supplies only visible records, with the query chain already removed."""
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError('Smoothing alpha must be positive and finite.')
    records = [(record, read_attributes(record, schema)) for record in records]
    models = {}
    for attribute, domain in schema['domains'].items():
        fleet = Counter()
        by_part, by_model = {}, {}
        for record, attributes in records:
            value = attributes[attribute]
            fleet[value] += 1
            name = str(record.get('part_name', '')).strip().upper()
            by_part.setdefault(name, Counter())[value] += 1
            if aircraft_model and record.get('aircraft_model') == aircraft_model:
                by_model.setdefault(name, Counter())[value] += 1
        models[attribute] = likelihood_from_counts(domain, hypothesis_names, fleet, by_part, by_model, alpha=alpha)
    return models


def likelihood_from_counts(domain, names, fleet, by_part, by_model, *, alpha=5):
    if not domain or len(set(domain)) != len(domain) or alpha <= 0 or not math.isfinite(alpha):
        raise ValueError('Likelihood domain/alpha are invalid.')
    if any(v not in domain or n < 0 for v, n in fleet.items()):
        raise ValueError('Fleet counts are outside the frozen vocabulary or negative.')
    total = sum(fleet.values())
    marginal = [fleet.get(value, 0) / total for value in domain] if total else [1 / len(domain)] * len(domain)
    matrix, scopes = [], []
    for name in names:
        name = name.strip().upper()
        local = by_model.get(name, Counter())
        selected = local if sum(local.values()) >= 20 else by_part.get(name, Counter())
        if any(v not in domain or n < 0 for v, n in selected.items()):
            raise ValueError('Part counts are invalid.')
        n = sum(selected.values())
        matrix.append([(selected.get(value, 0) + alpha * p) / (n + alpha) for value, p in zip(domain, marginal)])
        scopes.append({'part_name': name, 'scope': 'same_model' if sum(local.values()) >= 20 else 'fleet', 'n': n})
    matrix.append(marginal)  # other is always the visible fleet distribution.
    _validate([1 / len(matrix)] * len(matrix), matrix)
    return {'values': list(domain), 'matrix': matrix, 'fleet_n': total, 'scopes': scopes, 'alpha': alpha}


def select_question(prior, models, *, excluded=(), codebook, strategy='information_gain', rng=None):
    if strategy not in ('information_gain', 'random') or (strategy == 'random' and rng is None):
        raise ValueError('Unknown strategy or missing seeded random generator.')
    choices = []
    for attribute, model in models.items():
        if attribute in excluded:
            continue
        gain = expected_information_gain(prior, model['matrix'])
        indices = [i for i in range(len(model['values'])) if sum(p * row[i] for p, row in zip(prior, model['matrix'])) > 0]
        # A single possible answer cannot reduce uncertainty.
        if len(indices) < 2:
            continue
        choices.append((attribute, gain, indices))
    if not choices:
        return None
    choices.sort(key=lambda c: (-c[1], c[0]))
    attribute, gain, indices = rng.choice(choices) if strategy == 'random' else choices[0]
    model = models[attribute]
    return {'attribute': attribute, 'text': question_text(attribute), 'gain_bits': gain,
            'prior_entropy': entropy(prior),
            'reason': f"Expected to remove {gain:.3f} of {entropy(prior):.3f} bits of uncertainty.",
            'options': [{'value': model['values'][i], 'label': option_label(attribute, model['values'][i], codebook)} for i in indices],
            'model': model}


def answer_question(prior, question, value):
    if value == NOT_SURE:
        return list(prior)
    allowed = {option['value'] for option in question['options']}
    if value not in allowed:
        raise ValueError('Answer is not among the offered options.')
    return posterior(prior, question['model']['matrix'], question['model']['values'].index(value))
