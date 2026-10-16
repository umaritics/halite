---
id: mod-maintenance-api
title: Maintenance API
status: active
owners: [Usman]
updated: 2026-10-16
depends_on: [ctx-data-graph]
---

# Module: Maintenance API

## Purpose

Expose the Mid-I asset, history, ingest, record-processing, and review-queue
contracts under `/api/maintenance`.

## Primary files

| File | Role |
| --- | --- |
| `backend/api/routes/maintenance.py` | HTTP contracts and controlled errors |
| `backend/graph/queries.py` | GraphRepository reads/writes used by the API |
| `backend/agents/maintenance_agent.py` | Validated, idempotent FAA ingestion |
| `backend/tests/test_api_maintenance.py` | Endpoint and failure-path coverage |
| `backend/tests/test_graph_maintenance.py` | Memory/Neo4j repository contract coverage |

## Asset-list performance contract

`GET /api/maintenance/assets` calls
`GraphRepository.list_assets_with_counts()` exactly once. Neo4j performs one
`OPTIONAL MATCH` aggregation and returns `record_count` with each asset. The
memory implementation counts `ABOUT` edges in one pass. The route must not
load each asset's full history to calculate a count.

Mid-I staging target: one graph query (or a small constant) and less than
2–3 seconds for the approximately 2,079-record corpus. Redis is not part of
this fix; correct query shape comes first.

## Failure and safety behavior

- Unknown asset history returns 404; a known asset with no history returns an
  empty list.
- Ingest validates positive limits, skips invalid rows explicitly, and is
  duplicate-safe.
- Rejection requires a non-blank note; completed reviews cannot be overwritten.
- Model-dependent record processing fails with 503 when live inference is
  unavailable rather than fabricating a classification.
- Conflict and diagnostic caches are optional optimizations. A clean checkout
  or read-only cache path must not break classification/diagnosis behavior.

## Related

- Ingest: [`FLOW-ingest.md`](../../flows/FLOW-ingest.md)
- Review: [`FLOW-conflict-review.md`](../../flows/FLOW-conflict-review.md)
- Performance handoff: [`docs/mid1/10_perf_assets_api_handoff.md`](../../../docs/mid1/10_perf_assets_api_handoff.md)
