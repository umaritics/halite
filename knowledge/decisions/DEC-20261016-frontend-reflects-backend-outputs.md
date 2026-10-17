---
id: DEC-20261016-frontend-reflects-backend-outputs
title: The frontend only adds to, and never hides or alters, backend outputs
status: accepted
owners: [Shahmeer]
updated: 2026-10-16
---

# DEC-20261016 — Frontend reflects backend outputs

## Context

Umar (diagnostics) and Usman (maintenance APIs, conflict engine) own the backend behaviour and its outputs. An audit of the frontend
against live responses found places where the UI omitted or withheld what their endpoints return: the ranking `score`,
`context_size.wall_clock_s`, record ids beyond the first five per check, the model's text when evidence was empty, `confidence`,
`jasc_code` and `source` on asset history, and the `/api/health` runtime flags and `git_sha` (AGENTS.md: never claim live without
`/api/health` agreeing).

## Decision

The UI reflects backend outputs; it may add presentation, labels and warnings but must not hide, alter, or invent values.
- Show returned fields as sent. Label heuristics honestly (`score` is a "rank score", not a probability).
- Where output is unsupported (model text with no evidence) show it, labelled as unsupported, rather than withholding it.
- A field the backend did not send is omitted; it is never rendered as `false`, `No`, or a made-up default.
- Software-domain screens are out of scope and stay unreachable (see DEC-20261016-frontend-maintenance-only).

## Consequences

- New backend fields should be surfaced here in the same change, or listed as intentionally not shown.
- Removing a displayed field needs a new DEC. Tests: `Diagnostics`, `AssetHistory`, `ServiceRecords`, `Settings`.
- Service Records is now fleet-wide and paginated by a backend endpoint (DEC-20261017-fleet-service-records, which superseded the per-aircraft
  decision). A missing view should be solved by a backend endpoint, not a frontend workaround.
