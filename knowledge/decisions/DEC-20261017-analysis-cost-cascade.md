---
id: dec-analysis-cost-cascade
title: Pre-register the opt-in conflict-analysis cost cascade
status: accepted
owners: [Umar, Usman, Shahmeer]
updated: 2026-10-17
---

# DEC-20261017 — Conflict-analysis cost cascade

## Context

The current 2,079-record corpus sends 1,835 top-ranked pairs through five model
passes (9,175 requests). The free-tier token quota binds before the request
quota. The team lead waived normal Mid-I ownership for the conflict engine,
Groq adapter, maintenance analysis API/scripts, tests, evidence, and the small
method tooltip in this round. Copilot, Graph, and other pages remain out of
scope.

## Decision

- Keep `MAINT_ANALYSIS_MODE=legacy` as the default. `cascade` is opt-in until
  live validation in round four.
- Pre-register `CASCADE_SCREEN_THRESHOLD = 0.79`, selected only on the 141
  development ground-truth pairs. No held-out-year data was inspected.
- The screen score is prose containment/Jaccard after boilerplate and explicit
  `SUPPLEMENTAL REPORT FOR <ID>` removal, plus small exact part/JASC/location
  bonuses. Same-day is never a screen feature or filter.
- Rank by older-text containment first, then the existing integer score and
  deterministic legacy tie-breakers.
- Cascade inference uses two passes and stops on agreement; disagreement runs
  three more passes. Persist every vote and returned usage. An unresolved
  split routes to review.
- A persistent UTC-day budget stops at 90% of configured request or token
  limits and resumes without billing cache hits.

## Development evidence at registration

Threshold `0.79` retained 141/141 true pairs. Containment-first ranking put the
true pair first for 136/141 versus 124/141 under legacy ranking. On the current
corpus it screened 804 of 1,835 model-eligible records (43.8%). These are
offline development figures, not held-out or live-model validation.

## Consequences

Legacy outputs remain the deployment default. The cascade can be measured and
tested without silently changing production. Round four must validate model
quality, actual token usage, and the full run before making cascade the default.
