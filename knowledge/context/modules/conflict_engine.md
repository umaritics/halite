---
id: mod-conflict
title: Conflict engine module
status: active
owners: [Usman]
updated: 2026-10-16
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

1. **Candidate pairing** — same-asset history, heuristic score, cap (`MAINT_MAX_CANDIDATES`, often 25).
2. **Classify** — LLM JSON label (`supersedes`, `partial_supersedes`, `contradicts`, `no_conflict`, `scope_disjoint`) with cache.
3. **Adjudicate + confidence** — evidence signals (citation language, recency, authority, part/JASC agreement).
4. **Route** — high-risk labels → `needs_review`; else confidence vs `MAINT_CONFIDENCE_THRESHOLD`.

## Design constraints

- Do not raise threshold only to beautify demos.
- Preserve original records on accept/reject; do not claim adjudicated *diagnosis*.
- Conflict metrics ≠ diagnostic accuracy.

## Staging caveat (Mid-I)

Bulk ingest leaves all records at `auto_accepted` / `confidence=1.0` until `process_record` or `scripts/backfill_conflict_scores.py` runs. Empty Review Queue + all confidence=1 → see [`docs/mid1/16_usman_conflict_score_backfill_handoff.md`](../../../docs/mid1/16_usman_conflict_score_backfill_handoff.md).

The backfill command fails closed unless `GroqService.is_live` is true and
calls `process_record(..., allow_stub=False)`. Cached or canned stub output
must never be persisted as staging conflict evidence.

Records with no older candidate persist the engine's real result
(`auto_accepted`, confidence `0.0`, zero candidates) instead of retaining the
ingest placeholder confidence `1.0`. Resume mode processes only untouched
`auto_accepted`/`1.0` records with no classification label, preserving
supersessions, review states, and prior scored results.

## Related

[FLOW-conflict-review.md](../../flows/FLOW-conflict-review.md)
