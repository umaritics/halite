---
id: DEC-20261016-frontend-maintenance-only
title: Frontend is maintenance-only; legacy software UI is unreachable
status: accepted
owners: [Shahmeer]
updated: 2026-10-16
---

# DEC-20261016 — Frontend maintenance-only

## Context

The app opened on the software domain (Chat, Decisions, Alerts) with a domain toggle; the Review Queue badge used the
software alerts count; Settings (reachable from the maintenance nav) had "Reset knowledge graph", which runs
`MATCH (n) DETACH DELETE n` and would erase the loaded corpus in one click. The Mid-I blueprint requires maintenance-only
navigation and forbids destructive wipes of the demo dataset.

## Decision

- `DomainContext` is fixed to `maintenance`; a stale `halite.domain=software` in localStorage is ignored.
- Sidebar lists maintenance destinations only; the domain switcher is not rendered.
- `/app/chat|decisions|ingest|alerts` and unknown paths redirect to `/app/assets`.
- Settings keeps Theme and System Status only; "Reset knowledge graph" and "Agent context export" were removed.
- The review badge uses `GET /maintenance/review-queue`.
- Software pages and `DomainSwitcher` stay in the repo (isolated, not deleted).

## Consequences

- Reinstating any software screen needs a new DEC.
- `DELETE /api/graph/reset` still exists on the backend (Usman); removing the UI button does not protect the API.
- Tests: `DomainContext`, `Sidebar`.

Update 2026-10-18: the backend route is now protected by the operations token; see [DEC-20261018-protect-graph-reset](DEC-20261018-protect-graph-reset.md).
