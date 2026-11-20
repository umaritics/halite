"""
Baseline B0 — frozen mid-term heuristic ranker.

Benchmark harnesses import ranking from here so B0 stays fixed while B1+ evolve
in services/diagnostic_retrieval.py (or backend/retrieval/ after split).

Adopted with docs/plan/BENCHMARK_PROTOCOL.md on 2026-11-20.
"""
from evaluation.rank_b0 import (  # noqa: F401
    build_diagnostic_context_b0 as build_diagnostic_context,
    rank_diagnostic_checks_b0 as rank_diagnostic_checks,
)
from services.diagnostic_retrieval import (  # noqa: F401
    RANK_SUPERSEDED_PENALTY,
    RANK_WEIGHT_ASSET_HISTORY,
    RANK_WEIGHT_FLEET_MATCH,
)

BASELINE_ID = "B0"
BASELINE_DESCRIPTION = (
    "Mid-I deterministic ranker: asset history (recency) + fleet lexical overlap, "
    "documented weights, superseded penalty on status."
)