---
id: technical-registry
title: Module registry (code ↔ ownership ↔ docs)
status: active
owners: [all]
updated: 2026-11-16
---

# Module registry

> The "Primary owner (Mid-I)" column is historical. Since 2026-11-20 ownership is by vertical: see
> [DEC-20261120-vertical-ownership](decisions/DEC-20261120-vertical-ownership.md) and `docs/plan/CONTRACTS.md`.
> Update each row as the preparation pull requests move its files.

| Module | Primary owner (Mid-I) | Primary code | Context | Flow |
| --- | --- | --- | --- | --- |
| Diagnostics retrieval, ranking & copilot | Umar (cross-owner waiver for copilot) | `backend/services/diagnostic_retrieval.py`, `backend/api/routes/diagnostics.py`, `backend/services/groq_service.py` | [modules/diagnostics.md](context/modules/diagnostics.md) | [FLOW-diagnose.md](flows/FLOW-diagnose.md) |
| Graph schema & maintenance queries | Umar (cross-owner waiver for this task) | `backend/graph/schema.py`, `backend/graph/repo/{core,retrieval,integrity,legacy}.py`, `backend/graph/memory/`, compatibility `backend/graph/queries.py`, `backend/graph/neo4j_client.py` | [04_data_and_graph.md](context/04_data_and_graph.md) | FLOW-diagnose, FLOW-ingest, FLOW-conflict-review |
| Conflict engine + analysis migration/backfill | Usman (cross-owner waiver for this task) | `backend/services/conflict_engine.py`, `backend/services/conflict_screen.py`, `backend/services/analysis_budget.py`, `backend/scripts/migrate_conflict_analysis_state.py`, `backend/scripts/backfill_conflict_scores.py`, `backend/scripts/benchmark_local_llm_gt.py` | [modules/conflict_engine.md](context/modules/conflict_engine.md) | [FLOW-conflict-review.md](flows/FLOW-conflict-review.md) |
| Maintenance APIs (records/analysis/corrections/assets/history/review/ingest) | Usman (cross-owner waiver for this task) | `backend/api/routes/maintenance.py`, `backend/agents/maintenance_agent.py` | [modules/maintenance_api.md](context/modules/maintenance_api.md) | FLOW-ingest, FLOW-conflict-review |
| Workspace identity, RBAC & audit store (M01) | Umar + Usman + Shahmeer | `backend/db/models/identity.py`, `backend/db/models/__init__.py`, `backend/db/session.py`, `backend/services/auth_service.py`, `backend/api/routes/auth.py`, `frontend/src/context/AuthContext.jsx`, `frontend/src/pages/Login.jsx`, `frontend/src/pages/AcceptInvite.jsx`, `frontend/src/pages/TeamAccess.jsx` | [03_architecture.md](context/03_architecture.md), [modules/frontend.md](context/modules/frontend.md) | FLOW-conflict-review, FLOW-deploy |
| App wiring / health / security | Usman + Umar | `backend/main.py`, `backend/config.py`, `backend/api/security.py`, `backend/api/router.py` | [modules/devops.md](context/modules/devops.md), [modules/remote_backend.md](context/modules/remote_backend.md) | FLOW-ci, FLOW-deploy |
| Frontend maintenance UX | Shahmeer | `frontend/src/pages/*`, `frontend/src/components/*`, `frontend/src/utils/*`, `frontend/src/api/client.js`, `frontend/.env.development`, `vercel.json` | [modules/frontend.md](context/modules/frontend.md) | FLOW-diagnose, FLOW-conflict-review |
| CI / Compose | Usman | `.github/workflows/ci.yml`, `docker-compose.yml` | modules/devops.md | [FLOW-ci.md](flows/FLOW-ci.md) |
| Shared staging deploy / ops | Umar + Usman | `.github/workflows/deploy-staging.yml`, `fetch-staging-logs.yml`, `docker-compose.vm.yml`, `backend/api/routes/ops.py`, `scripts/vm/run_analysis_backfill.sh`, `scripts/vm/setup_swap.sh`, `docs/local-llm-staging.md` | [modules/remote_backend.md](context/modules/remote_backend.md) | [FLOW-deploy.md](flows/FLOW-deploy.md) |
| LLM adapter (Groq + openai-compatible / Ollama) | Usman + Umar | `backend/services/groq_service.py`, `backend/config.py` (`LLM_PROVIDER`, `OPENAI_COMPAT_*`), `docker-compose.vm.yml` (`halite-ollama`) | [modules/remote_backend.md](context/modules/remote_backend.md), `docs/local-llm-staging.md` | FLOW-conflict-review, FLOW-diagnose |
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

## Backend foundation extension points

- Graph repository and memory mixins: `core.py` (shared steward Usman), `retrieval.py` (Umar), `integrity.py` (Shahmeer), `legacy.py` (isolated pending retirement). Existing facades remain valid.
- Identity tables remain in `backend/db/models/identity.py` (Umar); vertical extension modules are `evaluation.py` (Umar), `integrity.py` (Shahmeer), `sessions.py` (Usman), imported once by `db/models/__init__.py`.
- Authenticated summary routers: `backend/api/routes/{retrieval,evaluation,integrity,sessions}.py`; route registration in `backend/api/router.py`. Statistics start empty.
- Model adapter `backend/services/groq_service.py` (Usman) selects JSON format explicitly; prose is the default.
- Evidence and phase scope: `docs/work/usman/WORK_LOG.md`; decision: DEC-20261120-backend-foundation.
