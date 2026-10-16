---
id: technical-registry
title: Module registry (code ↔ ownership ↔ docs)
status: active
owners: [all]
updated: 2026-10-16
---

# Module registry

| Module | Primary owner (Mid-I) | Primary code | Context | Flow |
| --- | --- | --- | --- | --- |
| Diagnostics retrieval & ranking | Umar | `backend/services/diagnostic_retrieval.py`, `backend/api/routes/diagnostics.py` | [modules/diagnostics.md](context/modules/diagnostics.md) | [FLOW-diagnose.md](flows/FLOW-diagnose.md) |
| Graph schema & queries | Umar | `backend/graph/schema.py`, `backend/graph/queries.py`, `backend/graph/neo4j_client.py` | [04_data_and_graph.md](context/04_data_and_graph.md) | FLOW-diagnose, FLOW-ingest |
| Conflict engine | Usman | `backend/services/conflict_engine.py` | [modules/conflict_engine.md](context/modules/conflict_engine.md) | [FLOW-conflict-review.md](flows/FLOW-conflict-review.md) |
| Maintenance APIs (assets/history/review/ingest) | Usman | `backend/api/routes/maintenance.py`, `backend/agents/maintenance_agent.py` | [modules/maintenance_api.md](context/modules/maintenance_api.md) | FLOW-ingest, FLOW-conflict-review |
| App wiring / health | Usman | `backend/main.py`, `backend/config.py` | [modules/devops.md](context/modules/devops.md) | FLOW-ci |
| Frontend maintenance UX | Shahmeer | `frontend/src/pages/*`, `frontend/src/api/client.js` | [modules/frontend.md](context/modules/frontend.md) | FLOW-diagnose, FLOW-conflict-review |
| CI / Compose | Usman | `.github/workflows/ci.yml`, `docker-compose.yml` | modules/devops.md | [FLOW-ci.md](flows/FLOW-ci.md) |
| Shared staging deploy / ops | Umar + Usman | `.github/workflows/deploy-staging.yml`, `fetch-staging-logs.yml`, `docker-compose.vm.yml`, `backend/api/routes/ops.py` | [modules/remote_backend.md](context/modules/remote_backend.md) | [FLOW-deploy.md](flows/FLOW-deploy.md) |
| Domain registry | shared (freeze) | `backend/domains/*` | [03_architecture.md](context/03_architecture.md) | — |
| Legacy software domain | frozen / non-product | Decisions, Components, software ingest routes | [01_domain_scope_deferred.md](context/01_domain_scope_deferred.md) | — |

## Shared contracts (controlled owners)

| Contract | Owner | Consumers |
| --- | --- | --- |
| Diagnose request/response JSON | Umar | Shahmeer UI, tests |
| Maintenance/review JSON | Usman | Shahmeer UI, tests |
| Frontend Axios adapter (`client.js`) | Shahmeer | All UI pages |
| Router registration (`main.py`) | Usman | All backend routes |
| Graph schema fields | Umar | Usman proposes ingest fields via issue/PR note |
