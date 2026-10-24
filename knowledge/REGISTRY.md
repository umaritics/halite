---
id: technical-registry
title: Module registry (code ↔ ownership ↔ docs)
status: active
owners: [all]
updated: 2026-10-24
---

# Module registry

| Module | Primary owner (Mid-I) | Primary code | Context | Flow |
| --- | --- | --- | --- | --- |
| Diagnostics retrieval, ranking & copilot | Umar (cross-owner waiver for copilot) | `backend/services/diagnostic_retrieval.py`, `backend/api/routes/diagnostics.py`, `backend/services/groq_service.py` | [modules/diagnostics.md](context/modules/diagnostics.md) | [FLOW-diagnose.md](flows/FLOW-diagnose.md) |
| Graph schema & maintenance queries | Umar (cross-owner waiver for this task) | `backend/graph/schema.py`, `backend/graph/queries.py`, `backend/graph/neo4j_client.py` | [04_data_and_graph.md](context/04_data_and_graph.md) | FLOW-diagnose, FLOW-ingest, FLOW-conflict-review |
| Conflict engine + analysis migration/backfill | Usman (cross-owner waiver for this task) | `backend/services/conflict_engine.py`, `backend/services/conflict_screen.py`, `backend/services/analysis_budget.py`, `backend/scripts/migrate_conflict_analysis_state.py`, `backend/scripts/backfill_conflict_scores.py` | [modules/conflict_engine.md](context/modules/conflict_engine.md) | [FLOW-conflict-review.md](flows/FLOW-conflict-review.md) |
| Maintenance APIs (records/analysis/corrections/assets/history/review/ingest) | Usman (cross-owner waiver for this task) | `backend/api/routes/maintenance.py`, `backend/agents/maintenance_agent.py` | [modules/maintenance_api.md](context/modules/maintenance_api.md) | FLOW-ingest, FLOW-conflict-review |
| App wiring / health | Usman | `backend/main.py`, `backend/config.py` | [modules/devops.md](context/modules/devops.md) | FLOW-ci |
| Frontend maintenance UX | Shahmeer | `frontend/src/pages/*`, `frontend/src/utils/*`, `frontend/src/api/client.js`, `frontend/.env.development`, `vercel.json` | [modules/frontend.md](context/modules/frontend.md) | FLOW-diagnose, FLOW-conflict-review |
| CI / Compose | Usman | `.github/workflows/ci.yml`, `docker-compose.yml` | modules/devops.md | [FLOW-ci.md](flows/FLOW-ci.md) |
| Shared staging deploy / ops | Umar + Usman | `.github/workflows/deploy-staging.yml`, `fetch-staging-logs.yml`, `docker-compose.vm.yml`, `backend/api/routes/ops.py` | [modules/remote_backend.md](context/modules/remote_backend.md) | [FLOW-deploy.md](flows/FLOW-deploy.md) |
| Domain registry | shared (freeze) | `backend/domains/*` | [03_architecture.md](context/03_architecture.md) | — |
| Legacy software domain | frozen / non-product | Decisions, Components, software ingest routes | [01_domain_scope_deferred.md](context/01_domain_scope_deferred.md) | — |

## Shared contracts (controlled owners)

| Contract | Owner | Consumers |
| --- | --- | --- |
| Diagnose + copilot request/response JSON | Umar | Shahmeer UI, tests |
| Maintenance records/analysis/corrections/review JSON | Usman | Shahmeer UI, tests |
| Frontend Axios adapter (`client.js`) | Shahmeer | All UI pages |
| Router registration (`main.py`) | Usman | All backend routes |
| Graph schema fields | Umar | Usman proposes ingest fields via issue/PR note |
