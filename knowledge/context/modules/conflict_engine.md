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

## Related

[FLOW-conflict-review.md](../../flows/FLOW-conflict-review.md)
