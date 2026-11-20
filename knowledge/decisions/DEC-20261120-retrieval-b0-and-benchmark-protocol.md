---
id: dec-retrieval-b0-protocol
title: Freeze retrieval baseline B0 and adopt benchmark protocol
status: accepted
owners: [Umar]
updated: 2026-11-20
---

# DEC-20261120 — Freeze B0 and benchmark protocol

## Context

FYP-I Final master plan (`docs/final1/Halite_Master_Plan.docx`) requires measured retrieval baselines with year splits and a frozen mid ranker (B0) before hybrid work.

## Decision

1. Adopt `docs/plan/BENCHMARK_PROTOCOL.md` as the retrieval evaluation contract.  
2. Freeze **B0** exports in `backend/evaluation/baseline_b0.py` pointing at the pre-hybrid heuristic.  
3. **B1** bug fixes ship in `services/diagnostic_retrieval.py` (fleet exclude by asset UUID/tail, symptom-weighted history, superseded via `corrected_by`/status).

## Consequences

- Harnesses must import B0 from `baseline_b0.py`, not duplicate weights.  
- 2025 data remains test-only for all verticals.  
- Shahmeer/Usman contracts unchanged (`build_diagnostic_context` shape preserved; extra flags optional).