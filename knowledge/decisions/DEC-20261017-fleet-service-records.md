---
id: dec-fleet-service-records
title: Fleet-wide paginated Service Records and corrections
status: accepted
owners: [Umar, Usman, Shahmeer]
updated: 2026-10-17
---

# DEC-20261017 — Fleet-wide paginated Service Records

## Context

The per-aircraft page removed a 119-request fan-out but made fleet search
impossible. A store-level paginated endpoint retains the two-call initial-load
limit while making aircraft an optional filter.

## Decision

`GET /api/maintenance/records` filters, sorts, counts, and paginates in the
backing store. Service Records defaults to All aircraft, loads the asset list
and first record page only, and keeps filters in the URL. `GET
/api/maintenance/corrections` derives one row per `SUPERSEDES` edge with a live
summary. Review Queue exposes corrections as a sibling tab.

This supersedes
[DEC-20261016-service-records-per-aircraft](DEC-20261016-service-records-per-aircraft.md).

## Consequences

Initial page work remains at most two calls, there is no per-aircraft fan-out,
and pagination is deterministic (`occurred_at DESC`, `record_id ASC`). Neo4j
indexes record/date/status/analysis/component and Asset IDs; relationship
traversal uses Neo4j's native adjacency.
