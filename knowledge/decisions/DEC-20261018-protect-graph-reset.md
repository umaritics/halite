---
id: dec-protect-graph-reset
title: Graph reset needs the operations token
status: accepted
owners: [Usman, Umar, Shahmeer]
updated: 2026-10-18
---

# DEC-20261018 — `DELETE /api/graph/reset` is protected

## Context

`DELETE /api/graph/reset` wiped every node and relationship (`MATCH (n) DETACH DELETE n`
on a real Neo4j graph) with no authentication. The UI button was removed on 16 Oct
([DEC-20261016-frontend-maintenance-only](DEC-20261016-frontend-maintenance-only.md)), but
removing a button does not protect an API. The route was repeatedly listed as an open risk
in the evidence documents and the Mid report.

## Decision

- The route requires the operations token (`X-Ops-Token`), the same guard as `/analysis/run`
  and `/ops/logs`. If `OPS_TOKEN` is not configured on the server the route returns 503, so it
  is **off by default**.
- Wiping a real Neo4j database additionally needs `confirm=WIPE`; the in-memory graph used by
  tests does not.
- The unused `graphAPI.reset` helper is removed from the frontend client.
- `frontend/.env.local` and `.env.*.local` are added to `.gitignore`.
- Regression tests (`test_graph_reset_guard.py`) prove that an unauthenticated or
  unconfigured call changes nothing and that the Neo4j wipe query is not executed without both
  the token and the confirmation. They use a recording fake, never a real database.

## Consequences

The destructive path is closed on any deployment, including shared staging, once this change is
released. It does not add authentication for ordinary users; that remains FYP-1 Final work.
This crosses file ownership (`api/routes/graph.py`); it was made at the team's request and the
route owners should review it.
