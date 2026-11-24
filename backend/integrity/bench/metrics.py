"""Metrics for the benchmark, as pure functions so every number can be recomputed by hand.

A pair is {"label": 0 or 1, "predicted": bool}. Each ratio returns None when its denominator
is zero: "no positives" is not the same thing as "recall of zero", and a bootstrap must be able
to skip a resample where the metric does not exist.
"""
from __future__ import annotations

import math
import random


def bootstrap_interval(items, statistic, *, n_resamples: int = 1000, seed: int, level: float = 0.95):
    """Percentile bootstrap of statistic(items): resample items with replacement, take the middle level.

    Resamples where the statistic is undefined (None) are skipped; if fewer than half are
    defined the interval would describe a different population, so it is (None, None).
    """
    items = list(items)
    if not items:
        return None, None
    rng = random.Random(seed)
    values = []
    for _ in range(n_resamples):
        value = statistic([items[rng.randrange(len(items))] for _ in items])
        if value is not None:
            values.append(value)
    if len(values) * 2 < n_resamples:
        return None, None
    values.sort()
    tail = (1 - level) / 2
    low = values[min(len(values) - 1, int(tail * len(values)))]
    high = values[max(0, math.ceil((1 - tail) * len(values)) - 1)]
    return low, high


def percentile(values, share: float):
    """Nearest-rank percentile (share in 0..1) of a non-empty list."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def hit_rate(positives, ranks_key: str, ordering: str, k: int | None):
    """Share of positives whose true prior has a rank under this ordering and at most k.

    k=None means anywhere in the list. A null rank (the prior was never a candidate) is a miss.
    """
    if not positives:
        return None
    hits = 0
    for row in positives:
        rank = (row.get(ranks_key) or {}).get(ordering)
        hits += rank is not None and (k is None or rank <= k)
    return hits / len(positives)


def confusion(pairs) -> dict:
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for pair in pairs:
        if pair["predicted"]:
            counts["tp" if pair["label"] == 1 else "fp"] += 1
        else:
            counts["fn" if pair["label"] == 1 else "tn"] += 1
    return counts


def _ratio(numerator: int, denominator: int):
    return numerator / denominator if denominator else None


def precision(pairs):
    c = confusion(pairs)
    return _ratio(c["tp"], c["tp"] + c["fp"])


def recall(pairs):
    c = confusion(pairs)
    return _ratio(c["tp"], c["tp"] + c["fn"])


def f1(pairs):
    c = confusion(pairs)
    return _ratio(2 * c["tp"], 2 * c["tp"] + c["fp"] + c["fn"])


def false_link_rate(pairs):
    """False positives over ALL negatives: how often a correction is invented on an unrelated pair."""
    c = confusion(pairs)
    return _ratio(c["fp"], c["fp"] + c["tn"])
