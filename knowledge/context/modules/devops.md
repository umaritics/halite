---
id: mod-devops
title: DevOps, runtime, CI
status: active
owners: [Usman]
updated: 2026-10-16
---

# Module: DevOps / runtime

## Compose / local

- `docker-compose.yml` — Neo4j + backend + frontend (dev). Not production.
- Setup guide: `docs/mid1_setup.md`.
- Runtime smoke: `backend/scripts/verify_mid1_runtime.py` (synthetic fixture in CI).

## CI (`.github/workflows/ci.yml`)

Jobs: backend pytest (`DEMO_MODE=true`) against an ephemeral Neo4j 5 service,
frontend `npm test` + build, Docker Compose real-graph smoke. Repository
contract tests run against both memory and Neo4j in the backend job.

Triggers currently include `main`, `develop`, `usman`. Umar branch should be added when pushing Mid-I work (see decisions).

## Health semantics

| Field | Meaning |
| --- | --- |
| `graph_mode=neo4j` | Using Neo4j client path |
| `llm_mode=live` | Groq configured and live |
| `maintenance_corpus_loaded` | ≥1 ServiceRecord visible to health |

## Staging note (Usman audit)

Public VM `dev1.corp.curatech.pk/halite-api` was observed serving an **older** API without maintenance routes — do not treat as Mid-I proof until redeployed.
