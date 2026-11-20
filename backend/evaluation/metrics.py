"""Benchmark metrics for Suite B."""
from __future__ import annotations

import random
from typing import Iterable


def top_k_hit(ranked_parts: list[str], target: str, k: int) -> bool:
    if not target:
        return False
    return target in ranked_parts[:k]


def summarise_hits(hits: list[bool]) -> dict:
    n = len(hits)
    if n == 0:
        return {"n": 0, "top1": 0.0, "top3": 0.0, "top5": 0.0}
    top1 = sum(hits) / n
    return {"n": n, "top1": round(top1, 4)}


def bootstrap_top1_ci(hits: list[bool], samples: int = 1000, seed: int = 42) -> tuple[float, float]:
    if not hits:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(hits)
    stats: list[float] = []
    for _ in range(samples):
        draw = [hits[rng.randrange(n)] for _ in range(n)]
        stats.append(sum(draw) / n)
    stats.sort()
    lo = stats[int(0.025 * samples)]
    hi = stats[int(0.975 * samples) - 1]
    return (round(lo, 4), round(hi, 4))