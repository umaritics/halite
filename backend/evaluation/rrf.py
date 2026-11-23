"""Reciprocal rank fusion for part-level ranked lists."""
from __future__ import annotations

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    *,
    k: int = DEFAULT_RRF_K,
) -> list[dict]:
    if not ranked_lists:
        return []
    scores: dict[str, float] = {}
    evidence: dict[str, set[str]] = {}
    sources: dict[str, set[str]] = {}

    for ranked in ranked_lists:
        for item in ranked:
            part = item.get("part_name", "")
            if not part:
                continue
            rank = int(item.get("rank", 0))
            if rank < 1:
                continue
            scores[part] = scores.get(part, 0.0) + 1.0 / (k + rank)
            evidence.setdefault(part, set()).update(item.get("evidence_record_ids") or [])
            sources.setdefault(part, set()).update(item.get("sources") or [])

    merged = [
        {
            "part_name": part,
            "score": round(score, 6),
            "evidence_count": len(evidence.get(part, set())),
            "evidence_record_ids": sorted(evidence.get(part, set())),
            "sources": sorted(sources.get(part, set())),
        }
        for part, score in scores.items()
    ]
    merged.sort(key=lambda x: (-x["score"], -x["evidence_count"], x["part_name"]))
    for i, item in enumerate(merged, start=1):
        item["rank"] = i
    return merged