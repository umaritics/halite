---
id: DEC-20261016-service-records-per-aircraft
title: Service Records loads one aircraft's history at a time
status: superseded
owners: [Shahmeer]
updated: 2026-10-16
---

# DEC-20261016 — Service Records per aircraft

> Superseded by [DEC-20261017-fleet-service-records](DEC-20261017-fleet-service-records.md).

## Context

`docs/mid1/10_perf_assets_api_handoff.md` (root cause 2): Service Records fetched the history of every aircraft on mount
(1 assets call + one history call per aircraft, ~119 for 118 aircraft). Acceptance: initial load ≤ 2 API calls. The backend
has no paginated service-records endpoint.

## Decision

Option A from the handoff: load the aircraft list, then the history of one aircraft (default: most records); switching loads
only that aircraft. Selection lives in the URL (`?asset=<uuid>`).

## Measured (2026-10-16, production build against staging)

| Step | Calls |
| --- | --- |
| First load | assets (688 ms) + history for 813SK (1221 ms) = 2 page calls, plus the shell's `review-queue` badge call |
| Switch aircraft | 1 call (926 ms) |

## Consequences

- Fleet-wide search across all records is not available. Option B (a paginated `GET /maintenance/service-records`, Usman) would restore
  it; revisit if needed.
- Acceptance counting: "≤ 2" is met for calls the page initiates; the shell's badge call is shared by every page.
- Tests: `ServiceRecords.test.jsx` enforces the 118-aircraft request count and ignores stale responses.
