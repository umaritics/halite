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
Before migration, API reads identify an untouched `confidence=1.0` record with
no analysis metadata as `legacy_placeholder`, return null confidence and
`analysis_state=unscored`, and leave the stored graph value unchanged.
Backfill `--resume` and `POST /maintenance/analysis/run` select explicit
`analysis_state=unscored`; both require live Groq, use `allow_stub=False`, and
bound 429 retries. The API batch is ops-token protected and capped at 25.
Coverage is returned by `GET /maintenance/analysis/status`.

### Opt-in cost cascade

`MAINT_ANALYSIS_MODE=legacy` remains the default. In `cascade` mode, candidate
ties are reordered by meaningful older-text containment, with supplemental-ID
answer keys and generic boilerplate removed. Pairs below the pre-registered
0.79 text/scope score become deterministic `screen` decisions without a model
request. Remaining pairs use two votes, escalating to five only on initial
disagreement; a persistent split goes to review. Confidence scales the model
classification signal by vote agreement, never by the number of passes.

Every classification stores method, model, votes, passes, provider token
usage when available, agreement and timestamp in the cache and on the record
(votes are JSON text for Neo4j property compatibility). A UTC-day budget is
persisted per model and stops before 90% of configured request or token caps.
Cache hits do not debit it. `/analysis/status` groups stored results by method,
and `/analysis/run` returns its stop reason and remaining budget.

The effective threshold is 0.50. The 2026-10-17 real-corpus preflight found
1,835 model-eligible records under current positive-score pairing, materially
different from the old “roughly 460” evidence. Do not tune pairing or routing
to fit that old count without a ground-truth evaluation. See
`docs/mid1/19_confidence_and_corrections_evidence.md`.
The cascade’s offline evidence is in
`docs/mid1/21_analysis_cascade_evidence.md`; live quality remains for the
next round.

## Related

[FLOW-conflict-review.md](../../flows/FLOW-conflict-review.md)
