---
id: DEC-20261016-branch-from-usman
title: Branch Umar Mid-I work from origin/usman
status: accepted
owners: [Umar]
updated: 2026-10-16
---

# DEC-20261016 — Branch from Usman

## Context

Work division specifies Umar branch `feat/mid1/graph-diagnostics` and Usman DevOps on `usman`. Umar’s graph/diagnostics must integrate with Usman’s CI, Compose, maintenance APIs, and evidence docs.

## Decision

Create Umar Mid-I work from `origin/usman` @ `b949de4` (not from stale `feat/maintenance-domain` alone).

**Supersession (same day):** the temporary name `feat/mid1/graph-diagnostics` was replaced by **`umar/mid1-graph-diagnostics`** as the sole team-facing Umar branch; the `feat/*` remote ref was deleted.

## Consequences

- Inherits CI workflow, mid1 setup/evidence, runtime smoke script, README overhaul.
- Also inherits open blockers (frontend CI red, real-corpus local Docker issues — later unblocked via staging).
- Team referral branch: `umar/mid1-graph-diagnostics`.
