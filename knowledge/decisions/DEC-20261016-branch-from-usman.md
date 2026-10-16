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

Create `feat/mid1/graph-diagnostics` from `origin/usman` @ `b949de4` and implement U1–U5 on top of that baseline (not from stale `feat/maintenance-domain` alone).

## Consequences

- Inherits CI workflow, mid1 setup/evidence, runtime smoke script, README overhaul.
- Also inherits open blockers (frontend CI red, real-corpus local Docker issues, stale VM).
- Push should eventually set upstream to `origin/feat/mid1/graph-diagnostics` and extend CI `on.push.branches` to include this branch.
