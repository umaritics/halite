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

Backend installs `requirements-dev.txt`, runs Ruff with runtime-error rules
(`E9`, `F63`, `F7`, `F82`), then pytest with terminal and XML coverage plus JUnit.
Coverage/JUnit artifacts upload even after a failure. API/agent/service/graph/DB/
investigation coverage is reported; no unsupported whole-project 80% claim is made.

Ephemeral Neo4j 5 and PostgreSQL 16 services run both repository and session
contract tests. PostgreSQL session fixtures use a random schema and remove only
that schema. `SESSION_TEST_DATABASE_URL` must refer to a disposable test server.
Frontend tests/build and the Compose real-graph smoke remain independent jobs.
Pull requests run CI; push triggers include main/develop/usman and Umar's old
implementation branch. Staging deployment is a separate main-only gated workflow.

## Health semantics

| Field | Meaning |
| --- | --- |
| `graph_mode=neo4j` | Using Neo4j client path |
| `llm_mode=live` | Configured provider path (Groq or compatible adapter) |
| `maintenance_corpus_loaded` | ≥1 ServiceRecord visible to health |

## Evidence and operations

Historical Mid-I failures are documented in `docs/mid1/`; they are not current
runtime evidence. Current local evidence is in `docs/work/usman/WORK_LOG.md`.
Use `/api/health` before claiming graph/model/corpus state. Shared staging,
its backup and deployments belong to Umar under the vertical plan. This work
uses only disposable local databases and draft review branches.
