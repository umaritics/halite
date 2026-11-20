"""Suite B — resolution prediction on citation-valid correction pairs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

import pandas as pd

from evaluation.corpus import _normalise_part, load_sdr_raw
from evaluation.graph_builder import build_eval_repository
from evaluation.metrics import bootstrap_top1_ci, top_k_hit
from evaluation.rank_b0 import build_diagnostic_context_b0, rank_diagnostic_checks_b0
from services.diagnostic_retrieval import build_diagnostic_context, rank_diagnostic_checks

RankerId = Literal["b0", "b1"]

_BUILDERS: dict[RankerId, tuple[Callable, Callable]] = {
    "b0": (build_diagnostic_context_b0, rank_diagnostic_checks_b0),
    "b1": (build_diagnostic_context, rank_diagnostic_checks),
}


@dataclass
class SuiteBConfig:
    raw_dir: Path
    pairs_path: Path
    splits_path: Path | None = None
    split: Literal["train", "tune", "test", "all"] = "test"
    max_pairs: int | None = None


def _load_pairs(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    df["_part_target"] = df["superseding_part"].map(_normalise_part)
    return df


def _split_years(splits_path: Path | None, split: str) -> set[str]:
    if split == "all" or not splits_path or not splits_path.is_file():
        return set()
    data = json.loads(splits_path.read_text(encoding="utf-8"))
    key = {"train": "train_years", "tune": "tune_years", "test": "test_years"}[split]
    return {str(y) for y in data.get(key, [])}


def run_suite_b(config: SuiteBConfig, ranker: RankerId = "b1") -> dict:
    corpus = load_sdr_raw(config.raw_dir)
    corpus = corpus[corpus["_submitted_dt"].notna()].sort_values("_submitted_dt")
    corpus_index = corpus.set_index("OperatorControlNumber")

    pairs = _load_pairs(config.pairs_path)
    years = _split_years(config.splits_path, config.split)
    if years:
        pairs = pairs[pairs["source_year"].isin(years)]

    if config.max_pairs is not None:
        pairs = pairs.head(config.max_pairs)

    build_ctx, rank_fn = _BUILDERS[ranker]
    hits1: list[bool] = []
    hits3: list[bool] = []
    hits5: list[bool] = []
    skipped = 0

    for _, pair in pairs.iterrows():
        old_id = pair["superseded_record_id"]
        new_id = pair["superseding_record_id"]
        target = pair["_part_target"]
        if not target:
            skipped += 1
            continue
        if old_id not in corpus_index.index:
            skipped += 1
            continue
        old_row = corpus_index.loc[old_id]
        query_time = old_row["_submitted_dt"]
        if query_time is None or pd.isna(query_time):
            skipped += 1
            continue
        if isinstance(query_time, pd.Timestamp):
            query_time = query_time.to_pydatetime()
        if query_time.tzinfo is None:
            query_time = query_time.replace(tzinfo=timezone.utc)

        tail = old_row["RegistryNNumber"].strip() or pair["tail_number"].strip()
        symptom = old_row["Discrepancy"].strip()
        if not tail or not symptom:
            skipped += 1
            continue

        repo, asset_id = build_eval_repository(
            corpus,
            tail,
            query_time,
            exclude_record_ids={new_id},
        )
        ctx = build_ctx(repo, asset_id, symptom)
        ranked = rank_fn(ctx)
        parts = [_normalise_part(r.get("part_name", "")) for r in ranked]
        parts = [p for p in parts if p]

        hits1.append(top_k_hit(parts, target, 1))
        hits3.append(top_k_hit(parts, target, 3))
        hits5.append(top_k_hit(parts, target, 5))

    n = len(hits1)
    ci = bootstrap_top1_ci(hits1) if hits1 else (0.0, 0.0)
    return {
        "suite": "B",
        "ranker": ranker,
        "split": config.split,
        "pairs_evaluated": n,
        "pairs_skipped": skipped,
        "top1_accuracy": round(sum(hits1) / n, 4) if n else 0.0,
        "top3_accuracy": round(sum(hits3) / n, 4) if n else 0.0,
        "top5_accuracy": round(sum(hits5) / n, 4) if n else 0.0,
        "top1_ci_95": list(ci),
    }