---
id: dec-conflict-analysis-state
title: Persist honest conflict-analysis state separately from confidence
status: accepted
owners: [Umar, Usman, Shahmeer]
updated: 2026-10-17
---

# DEC-20261017 — Honest conflict-analysis state

## Context

Bulk ingest formerly stored `auto_accepted` and `confidence=1.0` without running
the engine. The UI therefore displayed “certainty” for records that had never
been analysed. The team lead explicitly waived Mid-I file ownership for this
cross-backend/frontend correction.

## Decision

- Ingest stores `status=unscored`, `analysis_state=unscored`, and
  `confidence=null`.
- `analysis_state` is additive and has four values:
  - `unscored`: conflict analysis has not completed.
  - `scored`: analysis completed and does not require a reviewer. This includes
    `no_candidates`, which uses score `0`, label `no_candidates`, and model
    `none` because no LLM call occurred.
  - `needs_review`: analysis completed but routing requires a human.
  - `reviewed`: a reviewer accepted or rejected the queued record.
- Stored metadata includes `scored_at`, classification label/rationale,
  `candidate_count`, and `analysis_model`.
- A superseded older record does not display confidence. It displays the
  incoming `SUPERSEDES` record as “Corrected by <id>”.
- The dry-run migration recognizes only `confidence=1.0` records with no
  analysis metadata and preserves `legacy_confidence`/`legacy_status`.
- Until migration, API reads expose those untouched placeholders as unscored
  with `legacy_placeholder=true` and null confidence, without changing storage.
- Resume selects `analysis_state=unscored`; it never infers work state from a
  score. The effective threshold remains the evaluated `0.50`.
- Same-aircraft records with pairing score zero are not model candidates.
  Positive-score pairing remains broad and is not tuned to reproduce old
  evidence counts.

## Consequences

Old clients still receive `status` and `confidence`, while new clients can
distinguish missing analysis from a real score. Migration is reversible only
while a migrated record remains unscored. Live verification reports the model
and quota boundary; fallback output cannot be presented as live analysis.
