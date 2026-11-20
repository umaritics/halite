---
id: ctx-architecture
title: System architecture
status: active
owners: [all]
updated: 2026-10-16
---

# System architecture

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | React 18, Vite 5, JS/JSX, Tailwind, Axios, Vitest |
| Backend | FastAPI, Pydantic, SQLAlchemy 2, Argon2id, PyJWT, PyTest |
| Graph | Neo4j 5 (Compose / AuraDB) + in-memory fallback when `DEMO_MODE=true` or Neo4j unset |
| Relational (M01) | PostgreSQL 16 (`organizations`, `users`, `user_sessions`, `user_invites`, `audit_events`) + SQLite in-memory fallback in `DEMO_MODE=true` |
| LLM | Groq via `GroqService` (`is_live` gate); response caches for conflict + diagnose |

## Domain registry pattern

`backend/domains/registry.py` + adapters (`MaintenanceDomainAdapter`, software adapter). Maintenance is the Mid-I product domain; software adapter remains for regression.

## Runtime honesty (`/api/health`)

Critical fields: `demo_mode`, `graph_mode` (`neo4j`|`memory`), `using_memory_graph`, `llm_mode` (`live`|`fallback`), `maintenance_corpus_loaded`, `maintenance_record_count`. Never claim live Neo4j/LLM when health says otherwise.

## High-level dependency graph

```mermaid
flowchart LR
  UI[frontend React] --> API[FastAPI routes]
  API --> Maint[maintenance.py]
  API --> Diag[diagnostics.py]
  Diag --> Ret[diagnostic_retrieval.py]
  Diag --> Groq[groq_service.py]
  Maint --> Conf[conflict_engine.py]
  Maint --> Agent[maintenance_agent.py]
  Conf --> Groq
  Ret --> Graph[GraphRepository]
  Conf --> Graph
  Agent --> Graph
  Graph --> Neo4j[(Neo4j / memory store)]
```

## Design patterns in force

- **Adapter** for domain labels/rules.
- **Repository** (`GraphRepository`) over Neo4j/memory.
- **Pipeline** for conflict: candidates → classify → adjudicate → confidence → route.
- **Fail loud** for diagnose when LLM unavailable and no valid cache.
- **Citation allow-list**: only record IDs present in retrieved context may be confirmed.

Detail: legacy narrative in `docs/maintenance_architecture.md` (still valid for conflict/domain registry; prefer this bank for Mid-I navigation).

## Compatible vertical backend foundation

Graph methods now live in `backend/graph/repo/` and `backend/graph/memory/`;
`queries.py` and `memory_store.py` remain compatibility facades. Identity tables
live in `db/models/identity.py` with registered vertical extension modules.
Authenticated summary routers reserve each vertical's API namespace. Legacy
software remains isolated pending a separate retirement contract. Model prose
and structured extraction explicitly select different response formats.
See [backend_foundation.md](modules/backend_foundation.md) and
[FLOW-backend-foundation.md](../flows/FLOW-backend-foundation.md).
