"""B4 — graph-scope retrieval: same aircraft then same make/model, no text scoring."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from evaluation.corpus import _normalise_part
from evaluation.graph_builder import visible_before
from services.diagnostic_retrieval import RANK_WEIGHT_ASSET_HISTORY, RANK_WEIGHT_FLEET_MATCH


def _model_key(row: pd.Series) -> str:
    make = str(row.get("AircraftMake", "") or "").strip().upper()
    model = str(row.get("AircraftModel", "") or "").strip().upper()
    if not make and not model:
        return ""
    return f"{make}|{model}"


def rank_parts_graph(
    corpus: pd.DataFrame,
    tail_number: str,
    query_time: datetime,
    *,
    query_model_key: str | None = None,
    exclude_record_ids: set[str] | None = None,
    fleet_cap: int = 2500,
    same_model_cap: int = 80,
) -> list[dict]:
    """Rank parts from recency on own-aircraft history, then same make/model fleet."""
    visible = visible_before(corpus, query_time, exclude_record_ids, fleet_cap)
    if visible.empty:
        return []

    tail = tail_number.strip()
    own = visible[visible["RegistryNNumber"].str.strip() == tail].sort_values(
        "_submitted_dt", ascending=False
    )
    model_key = (query_model_key or "").strip().upper() or ""
    if not model_key and not own.empty:
        model_key = _model_key(own.iloc[0])

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

    for i, (_, row) in enumerate(own.iterrows()):
        recency = 1.0 / (i + 1)
        _add(
            row.get("PartName", ""),
            recency * RANK_WEIGHT_ASSET_HISTORY,
            "same_aircraft",
            row["OperatorControlNumber"],
        )

    if model_key:
        keys = visible.apply(_model_key, axis=1)
        peers = visible[
            (visible["RegistryNNumber"].str.strip() != tail) & (keys == model_key)
        ].sort_values("_submitted_dt", ascending=False).head(same_model_cap)
        for i, (_, row) in enumerate(peers.iterrows()):
            recency = 1.0 / (i + 1)
            _add(
                row.get("PartName", ""),
                recency * RANK_WEIGHT_FLEET_MATCH,
                "same_model",
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