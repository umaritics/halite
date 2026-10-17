---
id: mod-conflict
title: Conflict engine module
status: active
owners: [Usman, Umar]
updated: 2026-10-17
---

# Module: Conflict engine

## Purpose

Detect whether a new/updated `ServiceRecord` conflicts with or supersedes prior records on the same asset; route to auto-apply or human review.

## Primary files

| File | Owner |
| --- | --- |
| `backend/services/conflict_engine.py` | Usman |
| `backend/api/routes/maintenance.py` (process/review) | Usman |
| `backend/tests/test_conflict_engine.py` | Usman |

## Pipeline

1. **Candidate pairing** — same-asset history, positive heuristic score, cap (`MAINT_MAX_CANDIDATES`, often 25). Score-zero records are not candidates.
2. **Classify** — LLM JSON label (`supersedes`, `partial_supersedes`, `contradicts`, `no_conflict`, `scope_disjoint`) with cache.
3. **Adjudicate + confidence** — evidence signals (citation language, recency, authority, part/JASC agreement).
4. **Route** — high-risk labels → `needs_review`; else confidence vs `MAINT_CONFIDENCE_THRESHOLD`.

## Design constraints

- Do not raise threshold only to beautify demos.
- Preserve original records on accept/reject; do not claim adjudicated *diagnosis*.
- Conflict metrics ≠ diagnostic accuracy.

## Analysis state and operations

Ingest writes `unscored` with null confidence. The additive state machine is
`unscored` → `scored|needs_review` → `reviewed`. `no_candidates` is a real
`scored` result with zero comparisons, score 0, and no model call. A superseded
older record is presented through its incoming `SUPERSEDES` edge rather than a
confidence number.

The legacy migration is dry-run by default and preserves `legacy_confidence`.
Backfill `--resume` and `POST /maintenance/analysis/run` select explicit
`analysis_state=unscored`; both require live Groq, use `allow_stub=False`, and
bound 429 retries. The API batch is ops-token protected and capped at 25.
Coverage is returned by `GET /maintenance/analysis/status`.

The effective threshold is 0.50. The 2026-10-17 real-corpus preflight found
1,835 model-eligible records under current positive-score pairing, materially
different from the old “roughly 460” evidence. Do not tune pairing or routing
to fit that old count without a ground-truth evaluation. See
`docs/mid1/19_confidence_and_corrections_evidence.md`.

## Related

[FLOW-conflict-review.md](../../flows/FLOW-conflict-review.md)
