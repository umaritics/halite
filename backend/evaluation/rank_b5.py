"""B5 — reciprocal rank fusion of BM25 (B2), dense (B3), and graph (B4) part rankings."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from evaluation.embeddings import EmbeddingBackend
from evaluation.rank_b2 import rank_parts_bm25
from evaluation.rank_b3 import rank_parts_embed
from evaluation.rank_b4 import rank_parts_graph
from evaluation.rrf import DEFAULT_RRF_K, reciprocal_rank_fusion


def rank_parts_hybrid(
    corpus: pd.DataFrame,
    corpus_vectors: np.ndarray,
    backend: EmbeddingBackend,
    tail_number: str,
    symptom_text: str,
    query_time: datetime,
    *,
    exclude_record_ids: set[str] | None = None,
    fleet_cap: int = 2500,
    rrf_k: int = DEFAULT_RRF_K,
) -> list[dict]:
    ranked_b2 = rank_parts_bm25(
        corpus,
        tail_number,
        symptom_text,
        query_time,
        exclude_record_ids=exclude_record_ids,
        fleet_cap=fleet_cap,
    )
    ranked_b3 = rank_parts_embed(
        corpus,
        corpus_vectors,
        backend,
        tail_number,
        symptom_text,
        query_time,
        exclude_record_ids=exclude_record_ids,
        fleet_cap=fleet_cap,
    )
    ranked_b4 = rank_parts_graph(
        corpus,
        tail_number,
        query_time,
        exclude_record_ids=exclude_record_ids,
        fleet_cap=fleet_cap,
    )
    return reciprocal_rank_fusion([ranked_b2, ranked_b3, ranked_b4], k=rrf_k)