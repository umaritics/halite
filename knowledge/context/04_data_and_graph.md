---
id: ctx-data-graph
title: Data model and graph
status: active
owners: [Umar, Usman]
updated: 2026-10-16
---

# Data and graph

## Corpus

- Source: public FAA Service Difficulty Reports (SDR).
- Processed POC path (ignored by git): `backend/data/processed/sdr_poc_corpus.csv`.
- Typical POC scale (file evidence): ~2,079 records, ~118 assets; dense demo asset `813SK`.
- Licence notes: `docs/DATA_LICENCE.md`.

## Node types (maintenance)

| Label | Key ideas |
| --- | --- |
| `Asset` | Aircraft; `tail_number` / Registry N-number |
| `ServiceRecord` | One SDR filing; `record_id`, `occurred_at`, `text`, part/JASC fields, `status`, optional confidence/classification fields |

## Relationship types

| Type | Meaning | Provenance |
| --- | --- | --- |
| `ABOUT` | Record → Asset | From ingest |
| `PRECEDED_BY` | Chronological prior on same asset | From ingest ordering |
| `SUPERSEDES` | Newer record supersedes older | Computed by conflict engine when auto-accepted |

Do **not** invent causal “causes/fixes” edges without data justification (Mid-I deferred).

## Status values (service records)

Common: `auto_accepted`, `needs_review`, `accepted`, `rejected`, `superseded`, plus ingest defaults. Review queue = `status == needs_review`.

## Access patterns

- List assets / history: Usman routes in `maintenance.py`.
- Diagnostic context: Umar `asset_history_context`, `similar_symptom_records`, `build_diagnostic_context`.
- Always bound limits on dense assets (e.g. history `limit`).

## Modes

| Mode | When | Product claim |
| --- | --- | --- |
| Neo4j live | `DEMO_MODE=false` + Neo4j configured | Required for Mid-I “real data” demo |
| Memory | `DEMO_MODE=true` or Neo4j missing | Tests / degraded only — label honestly |
