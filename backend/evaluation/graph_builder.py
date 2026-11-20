"""Build an in-memory GraphRepository for one benchmark query."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository


def visible_before(
    corpus: pd.DataFrame,
    query_time: datetime,
    exclude_record_ids: set[str] | None = None,
    fleet_cap: int = 2500,
) -> pd.DataFrame:
    """Corpus slice with submission strictly before query_time (sorted corpus required)."""
    exclude = exclude_record_ids or set()
    end = int(corpus["_submitted_dt"].searchsorted(query_time, side="left"))
    visible = corpus.iloc[:end]
    if exclude:
        visible = visible[~visible["OperatorControlNumber"].isin(exclude)]
    return visible.sort_values("_submitted_dt", ascending=False).head(fleet_cap)


def build_eval_repository(
    corpus: pd.DataFrame,
    tail_number: str,
    query_time: datetime,
    *,
    exclude_record_ids: set[str] | None = None,
    fleet_cap: int = 2500,
) -> tuple[GraphRepository, str]:
    """
    Insert records visible strictly before ``query_time`` (leakage-safe).
    Returns (repository, asset_uuid).
    """
    fleet = visible_before(corpus, query_time, exclude_record_ids, fleet_cap)

    store = MemoryGraphStore()
    repo = GraphRepository(store)
    asset = repo.find_or_create_asset(tail_number, {})

    from evaluation.corpus import record_row_to_graph

    for _, row in fleet.iterrows():
        rec = record_row_to_graph(row)
        repo.create_service_record(rec)
        link_tail = row["RegistryNNumber"].strip()
        if link_tail == tail_number:
            repo.link_record_about_asset(rec["record_id"], asset["id"])

    return repo, asset["id"]