"""Deterministic bounded NLL fit; shared contract fits 2023, never 2025."""
from __future__ import annotations

import math

from investigation.beliefs import BeliefParameters


def _case(case):
    hypotheses = case['hypotheses'][:10]
    scores = [float(item['score']) for item in hypotheses]
    names = [str(item['part_name']).strip().upper() for item in hypotheses]
    target = str(case['answer_part']).strip().upper()
    if not target or len(set(names)) != len(names) or any(not name for name in names):
        raise ValueError('Cases require unique named hypotheses and a nonempty answer key.')
    if any(not math.isfinite(s) for s in scores):
        raise ValueError('Non-finite ranking score.')
    return scores, names.index(target) if target in names else len(names)


def negative_log_likelihood(cases, temperature, other_score):
    if not cases or not math.isfinite(temperature) or temperature <= 0 or not math.isfinite(other_score):
        raise ValueError('Nonempty cases and finite parameters are required.')
    total = 0.0
    for case in cases:
        scores, target = _case(case)
        scores.append(other_score)
        largest = max(scores)
        shifted = [(s - largest) / temperature for s in scores]
        total += math.log(sum(math.exp(s) for s in shifted)) - shifted[target]
    return total / len(cases)


def fit_parameters(cases, *, ranker_version, corpus_sha256):
    if not cases or any(case.get('year') != 2023 for case in cases):
        raise ValueError('Calibration fit accepts only nonempty 2023 cases.')
    if any(case.get('ranker_version') != ranker_version for case in cases):
        raise ValueError('All cases must use the fitted ranker version.')
    all_scores = [score for case in cases for score in _case(case)[0]]
    if not all_scores:
        raise ValueError('No named hypotheses available to fit.')
    low, high = min(all_scores), max(all_scores)
    scale = max(high - low, abs(high) * 0.01, 1e-3)
    # Explicit search domain, recorded for reproducibility and boundary diagnostics.
    log_min, log_max = math.log(scale / 100), math.log(scale * 100)
    c_min, c_max = low - 5 * scale, high + 5 * scale
    best = (math.inf, 0.0, 0.0)
    evaluations = 0
    def evaluate(log_t, c):
        nonlocal best, evaluations
        loss = negative_log_likelihood(cases, math.exp(log_t), c)
        evaluations += 1
        candidate = (loss, log_t, c)
        best = min(best, candidate)
    for i in range(21):
        for j in range(31):
            evaluate(log_min + (log_max - log_min) * i / 20, c_min + (c_max - c_min) * j / 30)
    log_step, c_step = (log_max - log_min) / 20, (c_max - c_min) / 30
    for _ in range(6):
        _, center_t, center_c = best
        for i in range(-3, 4):
            for j in range(-3, 4):
                evaluate(max(log_min, min(log_max, center_t + i * log_step / 3)),
                         max(c_min, min(c_max, center_c + j * c_step / 3)))
        log_step /= 3
        c_step /= 3
    loss, log_t, c = best
    params = BeliefParameters(ranker_version, math.exp(log_t), c, (2023,), corpus_sha256)
    at_boundary = (math.isclose(log_t, log_min) or math.isclose(log_t, log_max)
                   or math.isclose(c, c_min) or math.isclose(c, c_max))
    return {'parameters': params.as_dict(), 'mean_nll': loss, 'n': len(cases),
            'optimizer': 'bounded_grid_then_six_refinements-v1', 'evaluations': evaluations,
            'search_domain': {'temperature': [math.exp(log_min), math.exp(log_max)], 'other_score': [c_min, c_max]},
            'at_search_boundary': at_boundary}
