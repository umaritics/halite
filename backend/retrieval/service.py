"""
Product retrieval ranker (docs/plan/CONTRACTS.md §4.2).

``mid_heuristic`` / ``mid_fixed`` rank from the live graph.
``bm25``, ``dense``, and ``hybrid_rrf`` use the offline FAA SDR corpus when present.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from evaluation.rank_b0 import rank_diagnostic_checks_b0
from services import diagnostic_retrieval as legacy

_MODE_ALIASES = {
    "b0": "mid_fixed",
    "b1": "mid_heuristic",
    "b2": "bm25",
    "b3": "dense",
    "b5": "hybrid_rrf",
}

_RANKER_VERSION = {
    "mid_heuristic": "mid_heuristic-v1-b1",
    "mid_fixed": "mid_fixed-v0-b0",
    "bm25": "bm25-v1",
    "dense": "dense-v1-fastembed",
    "hybrid_rrf": "hybrid_rrf-v1",
    "graph": "graph-v0-stub",
    "hybrid_fitted": "hybrid_fitted-v0-stub",
}

_OFFLINE_MODES = frozenset({"bm25", "dense", "hybrid_rrf"})


def normalize_mode(mode: str | None) -> str:
    key = (mode or "mid_heuristic").strip().lower()
    return _MODE_ALIASES.get(key, key)


def ranker_version(mode: str | None) -> str:
    return _RANKER_VERSION.get(normalize_mode(mode), _RANKER_VERSION["mid_heuristic"])


def corpus_available() -> bool:
    return _resolve_raw_dir() is not None


def rank_checks_from_context(context: dict, mode: str | None) -> list[dict]:
    """One-shot /diagnose ranking from an already-built diagnostic context."""
    if normalize_mode(mode) == "mid_fixed":
        return rank_diagnostic_checks_b0(context)
    return legacy.rank_diagnostic_checks(context)


def _resolve_raw_dir() -> Path | None:
    try:
        from config import get_settings

        settings = get_settings()
        if getattr(settings, "RETRIEVAL_RAW_DIR", "").strip():
            base = Path(settings.RETRIEVAL_RAW_DIR)
        else:
            base = Path(settings.MAINT_DATA_DIR) / "raw"
        if base.is_dir() and list(base.glob("SDR-*.csv")):
            return base
    except Exception:
        pass
    return None


def _embedding_cache_dir() -> Path:
    from config import get_settings

    settings = get_settings()
    custom = getattr(settings, "RETRIEVAL_EMBEDDING_CACHE", "").strip()
    if custom:
        return Path(custom)
    return Path(settings.MAINT_DATA_DIR) / "evaluation"


def _asset_tail(graph_repo, asset_id: str | None) -> str:
    if not asset_id:
        return ""
    if hasattr(graph_repo, "list_assets_with_counts"):
        for asset in graph_repo.list_assets_with_counts():
            if str(asset.get("id") or "") == asset_id:
                return str(asset.get("tail_number") or "").strip()
    return ""


def _parse_as_of(as_of: str | datetime | None) -> datetime:
    if as_of is None:
        return datetime.now(timezone.utc)
    if isinstance(as_of, datetime):
        return as_of if as_of.tzinfo else as_of.replace(tzinfo=timezone.utc)
    return pd.to_datetime(as_of, utc=True).to_pydatetime()


def _active_copilot_context(context: dict, ruled_out: list[str]) -> dict:
    excluded = {legacy._normalise(value) for value in ruled_out if value}
    return {
        **context,
        "asset_history": [
            r for r in context.get("asset_history", []) if not r.get("is_superseded")
        ],
        "fleet_matches": [
            r for r in context.get("fleet_matches", []) if not r.get("is_superseded")
        ],
        "symptom_text": context.get("symptom_text") or "",
    }


def _filter_ruled_out(ranked: list[dict], ruled_out: list[str]) -> list[dict]:
    excluded = {legacy._normalise(value) for value in ruled_out if value}
    out = [
        item
        for item in ranked
        if legacy._normalise(item.get("part_name", "")) not in excluded
    ]
    for index, item in enumerate(out, start=1):
        item["rank"] = index
    return out


def _rank_offline_parts(
    graph_repo,
    asset_id: str | None,
    symptom_text: str,
    mode: str,
    as_of: str | datetime | None,
) -> list[dict]:
    from evaluation.corpus import load_sdr_raw
    from evaluation.embeddings import EmbeddingBackend, load_or_build_corpus_matrix
    from evaluation.rank_b2 import rank_parts_bm25
    from evaluation.rank_b3 import rank_parts_embed
    from evaluation.rank_b5 import rank_parts_hybrid

    raw_dir = _resolve_raw_dir()
    if not raw_dir:
        raise FileNotFoundError("SDR corpus not available under data/raw")
    corpus = load_sdr_raw(raw_dir)
    tail = _asset_tail(graph_repo, asset_id)
    query_time = _parse_as_of(as_of)
    nm = normalize_mode(mode)
    if nm == "bm25":
        return rank_parts_bm25(corpus, tail, symptom_text, query_time)
    backend = EmbeddingBackend(kind="fastembed")
    vectors = load_or_build_corpus_matrix(corpus, _embedding_cache_dir(), backend)
    if nm == "dense":
        return rank_parts_embed(
            corpus, vectors, backend, tail, symptom_text, query_time
        )
    if nm == "hybrid_rrf":
        return rank_parts_hybrid(
            corpus, vectors, backend, tail, symptom_text, query_time
        )
    raise ValueError(f"Unsupported offline ranker mode: {mode}")


def _evidence_index(context: dict) -> list[dict]:
    seen: dict[str, dict] = {}
    for record in [*context.get("asset_history", []), *context.get("fleet_matches", [])]:
        rid = record.get("record_id")
        if rid:
            seen.setdefault(rid, record)
    return list(seen.values())


def _rank_mid_graph(
    graph_repo,
    asset_id: str | None,
    state: dict,
    mode: str,
    k: int,
    as_of: str | datetime | None,
) -> dict[str, Any]:
    nm = normalize_mode(mode)
    if as_of is not None:
        raise ValueError(
            "Historical mid_heuristic ranking requires a prefiltered graph and as_of=None."
        )
    context = legacy.build_copilot_context(graph_repo, asset_id, state)
    active = _active_copilot_context(context, state.get("ruled_out", []))
    if nm == "mid_fixed":
        ranked = rank_diagnostic_checks_b0(active)
    else:
        ranked = legacy.rank_diagnostic_checks(active)
    hypotheses = _filter_ruled_out(ranked, state.get("ruled_out", []))[:k]
    return {
        "mode": nm,
        "ranker_version": ranker_version(nm),
        "hypotheses": hypotheses,
        "evidence": _evidence_index(context),
        "context_size": context["context_size"],
        "context": context,
        "warnings": [],
    }


def rank(
    graph_repo,
    *,
    asset_id: str | None = None,
    symptoms: list[str] | tuple[str, ...] = (),
    observations: list[str] | tuple[str, ...] = (),
    ruled_out: list[str] | tuple[str, ...] = (),
    as_of: str | datetime | None = None,
    mode: str | None = None,
    k: int = 10,
) -> dict[str, Any]:
    if not 1 <= k <= 10:
        raise ValueError("Investigation ranking supports one to ten hypotheses.")
    nm = normalize_mode(mode)
    warnings: list[str] = []
    state = {
        "symptoms": list(symptoms),
        "observations": list(observations),
        "ruled_out": list(ruled_out),
    }
    query = " ".join(
        [*(str(s).strip() for s in state["symptoms"]), *(str(o).strip() for o in state["observations"])]
    ).strip()

    if nm in _OFFLINE_MODES:
        if not query:
            warnings.append("Empty query; using mid_heuristic ranking.")
            return _rank_mid_graph(graph_repo, asset_id, state, "mid_heuristic", k, as_of)
        try:
            ranked = _rank_offline_parts(graph_repo, asset_id, query, nm, as_of)
        except FileNotFoundError:
            warnings.append(
                f"Requested ranker {nm} is unavailable (no SDR corpus); using mid_heuristic."
            )
            result = _rank_mid_graph(
                graph_repo, asset_id, state, "mid_heuristic", k, as_of
            )
            result["warnings"] = warnings
            return result
        context = legacy.build_copilot_context(graph_repo, asset_id, state)
        hypotheses = _filter_ruled_out(ranked, state["ruled_out"])[:k]
        return {
            "mode": nm,
            "ranker_version": ranker_version(nm),
            "hypotheses": hypotheses,
            "evidence": _evidence_index(context),
            "context_size": context["context_size"],
            "context": context,
            "warnings": warnings,
        }

    if nm in ("graph", "hybrid_fitted"):
        warnings.append(f"Ranker {nm} is not implemented; using mid_heuristic.")
        result = _rank_mid_graph(graph_repo, asset_id, state, "mid_heuristic", k, as_of)
        result["warnings"] = warnings
        return result

    return _rank_mid_graph(graph_repo, asset_id, state, nm, k, as_of)