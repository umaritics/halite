"""Pure, versioned score-to-belief conversion; scores are never probabilities by fiat."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class BeliefParameters:
    ranker_version: str
    temperature: float
    other_score: float
    fit_years: tuple[int, ...]
    corpus_sha256: str

    def __post_init__(self):
        if not self.ranker_version or not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError('A version and finite positive temperature are required.')
        if not math.isfinite(self.other_score):
            raise ValueError('other_score must be finite.')
        if self.fit_years != (2023,) or len(self.corpus_sha256) != 64:
            raise ValueError('Fitted parameters must identify the 2023 fit corpus SHA-256.')
        try:
            int(self.corpus_sha256, 16)
        except ValueError as exc:
            raise ValueError('Invalid corpus SHA-256.') from exc

    def as_dict(self):
        return {'ranker_version': self.ranker_version, 'temperature': self.temperature,
                'other_score': self.other_score, 'fit_years': list(self.fit_years),
                'corpus_sha256': self.corpus_sha256}


def load_parameters(path: str | Path, *, ranker_version: str) -> BeliefParameters:
    """An explicit file only; malformed/mismatched calibration never silently applies."""
    data = json.loads(Path(path).read_text())
    params = BeliefParameters(data['ranker_version'], float(data['temperature']), float(data['other_score']),
                             tuple(data['fit_years']), data['corpus_sha256'])
    if params.ranker_version != ranker_version:
        raise ValueError('Calibration belongs to a different ranker version.')
    return params


def entropy(values) -> float:
    values = list(values)
    if any(not math.isfinite(p) or p < 0 or p > 1 for p in values):
        raise ValueError('Beliefs must be finite values between zero and one.')
    if values and not math.isclose(sum(values), 1.0, abs_tol=1e-9):
        raise ValueError('Beliefs must sum to one.')
    return -sum(p * math.log2(p) for p in values if p > 0)


def score_beliefs(hypotheses: list[dict], *, ranker_version: str,
                  parameters: BeliefParameters | None = None) -> dict:
    """Stable softmax over top ten plus other; preserve the ranker's named order."""
    if not ranker_version:
        raise ValueError('ranker_version is required.')
    top = [dict(item) for item in hypotheses[:10]]
    names = [str(item.get('part_name', '')).strip() for item in top]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError('Ranked parts must have unique nonempty names.')
    scores = [float(item['score']) for item in top]
    if any(not math.isfinite(score) for score in scores):
        raise ValueError('Ranking scores must be finite.')
    if parameters and parameters.ranker_version != ranker_version:
        raise ValueError('Calibration belongs to a different ranker version.')
    temperature = parameters.temperature if parameters else 1.0
    other_score = parameters.other_score if parameters else min(scores, default=0.0)
    # Subtract before dividing: unlike s/T - max(s/T), this handles huge finite scores.
    all_scores = [*scores, other_score]
    highest = max(all_scores)
    weights = [math.exp((score - highest) / temperature) for score in all_scores]
    total = sum(weights)
    values = [weight / total for weight in weights]
    for item, value in zip(top, values):
        item['belief'] = value
    return {'hypotheses': top, 'other': values[-1], 'entropy': entropy(values),
            'calibrated': parameters is not None, 'label': 'relative support',
            'ranker_version': ranker_version, 'temperature': temperature,
            'other_score': other_score,
            'parameters': parameters.as_dict() if parameters else None}
