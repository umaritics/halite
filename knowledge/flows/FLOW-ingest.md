---
id: flow-ingest
title: Corpus ingest flow
status: active
owners: [Usman]
updated: 2026-10-16
---

# FLOW-ingest — FAA CSV to graph

## Happy path

1. `python scripts/fetch_sdr_data.py` (or use existing processed CSV).
2. `POST /api/maintenance/ingest` with default path `data/processed/sdr_poc_corpus.csv`.
3. `MaintenanceAgent` creates/updates `Asset` + `ServiceRecord`, `ABOUT`, chronological `PRECEDED_BY`.
4. Idempotent: second ingest skips duplicates (`duplicates_skipped`).
5. Health shows `maintenance_corpus_loaded` + non-zero count.

## Dependency graph

```mermaid
flowchart LR
  CSV[sdr_poc_corpus.csv] --> Route[maintenance.py /ingest]
  Route --> Agent[maintenance_agent.py]
  Agent --> GR[GraphRepository]
  GR --> N[(Neo4j)]
  Compose[docker-compose.yml] --> N
  Compose --> BE[backend container]
```

## Caveats

- Do not `docker compose down -v` against the only demo volume without backup.
- Real FAA corpus is gitignored; CI uses synthetic `mid1_smoke.csv`.
