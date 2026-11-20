"""B3 — dense embedding retrieval aggregated to part ranking (benchmark)."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from evaluation.corpus import _normalise_part
from evaluation.embeddings import EmbeddingBackend, cosine_scores_for_visible, doc_text
from evaluation.graph_builder import visible_before
from services.diagnostic_retrieval import (
    RANK_WEIGHT_ASSET_HISTORY,
    RANK_WEIGHT_FLEET_MATCH,
    _text_similarity,
)


def rank_parts_embed(
    corpus: pd.DataFrame,
    corpus_vectors: np.ndarray,
    backend: EmbeddingBackend,
    tail_number: str,
    symptom_text: str,
    query_time: datetime,
    *,
    exclude_record_ids: set[str] | None = None,
    fleet_cap: int = 2500,
    top_records: int = 40,
) -> list[dict]:
    visible = visible_before(corpus, query_time, exclude_record_ids, fleet_cap)
    if visible.empty:
        return []

    dense_scores = cosine_scores_for_visible(
        corpus_vectors, corpus, visible, symptom_text, backend
    )
    visible = visible.copy()
    visible["_dense"] = dense_scores

    own = visible[visible["RegistryNNumber"].str.strip() == tail_number]
    fleet = visible[visible["RegistryNNumber"].str.strip() != tail_number]
    fleet = fleet.sort_values("_dense", ascending=False).head(top_records)

    component_scores: dict[str, dict] = {}

    def _add(part: str, weight: float, source: str, record_id: str) -> None:
        key = _normalise_part(part)
        if not key:
            return
        if key not in component_scores:
            component_scores[key] = {
                "part_name": key,
                "score": 0.0,
                "evidence_count": 0,
                "evidence_record_ids": [],
                "sources": [],
            }
        bucket = component_scores[key]
        bucket["score"] += weight
        if record_id and record_id not in bucket["evidence_record_ids"]:
            bucket["evidence_count"] += 1
            bucket["evidence_record_ids"].append(record_id)
        if source not in bucket["sources"]:
            bucket["sources"].append(source)

    own_sorted = own.sort_values("_submitted_dt", ascending=False)
    for i, (_, row) in enumerate(own_sorted.iterrows()):
        sym = max(
            _text_similarity(symptom_text, row.get("Discrepancy", "")),
            _text_similarity(symptom_text, row.get("PartName", "")),
        )
        if sym < 0.05:
            continue
        recency = 1.0 / (i + 1)
        _add(
            row.get("PartName", ""),
            recency * sym * RANK_WEIGHT_ASSET_HISTORY,
            "asset_history",
            row["OperatorControlNumber"],
        )

    fleet_dense = fleet["_dense"].to_numpy(dtype=np.float32)
    max_dense = float(np.max(fleet_dense)) if len(fleet_dense) else 0.0
    for _, row in fleet.iterrows():
        raw = float(row["_dense"])
        norm = (raw / max_dense) if max_dense > 0 else 0.0
        if norm < 0.05:
            continue
        _add(
            row.get("PartName", ""),
            norm * RANK_WEIGHT_FLEET_MATCH,
            "fleet_dense",
            row["OperatorControlNumber"],
        )

    ranked = sorted(
        component_scores.values(),
        key=lambda x: (-x["score"], -x["evidence_count"], x["part_name"]),
    )
    for i, item in enumerate(ranked):
        item["rank"] = i + 1
        item["score"] = round(item["score"], 4)
        item["evidence_record_ids"] = sorted(item["evidence_record_ids"])
        item["sources"] = sorted(item["sources"])
    return ranked