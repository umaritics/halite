---
id: flow-backend-foundation
title: Backend registration and vertical delegation
status: active
owners: [Usman]
updated: 2026-11-20
---

# Backend foundation flow

1. `main.py` or the test app calls `register_api_routers` once.
2. The authenticated parent mounts each vertical summary router, retaining the
   existing API-key/JWT security dependency.
3. Existing graph imports resolve through compatibility facades to mixin classes.
   Core lifecycle/CRUD delegates retrieval and integrity methods without changing
   their existing memory or Cypher behavior.
4. `db.models` imports identity and all vertical extension modules before the
   relational store invokes `Base.metadata.create_all`.
5. Model prose requests omit JSON format; extraction explicitly requests JSON.
   Provider selection and key fallback preserve that choice and token accounting.

```mermaid
flowchart TB
  App[main.py or test app] --> Router[api/router.py]
  Router --> Auth[authenticated parent]
  Auth --> Summary[retrieval/evaluation/integrity/sessions summaries]
  App --> Models[db/models/__init__.py]
  Models --> Identity[identity.py unchanged tables]
  Models --> Extensions[evaluation.py / integrity.py / sessions.py]
  Identity --> Base[Base.metadata.create_all]
  Extensions --> Base
  Calls[existing graph callers] --> Facade[queries.py / memory_store.py]
  Facade --> Core[repo/core.py / memory/core.py]
  Core --> Retrieval[retrieval mixin]
  Core --> Integrity[integrity mixin]
  Core --> Legacy[isolated legacy mixin]
  Core --> Store[Neo4j or memory]
  Retrieval --> Store
  Integrity --> Store
  Prose[chat / chat_with_usage] --> Format[json_mode false]
  JSON[extract_json / extract_json_with_usage] --> JSONFormat[json_mode true]
  Format --> Provider[Groq or compatible HTTP]
  JSONFormat --> Provider
```

## Failure behavior

- Summary authentication inherits production fail-closed behavior.
- Empty summary statistics mean the vertical has not supplied its implementation.
- Existing graph/API failure semantics are unchanged.
- Provider failure and empty content are errors; output-format selection never
  substitutes invented records, explanations or citations.

## Software retirement and startup

```mermaid
flowchart TB
  Startup[Production lifespan] --> Choice[Configured graph mode]
  Choice --> Memory[Fresh empty memory store]
  Choice --> Neo4j[Connect / initialize schema; preserve existing data]
  Neo4j -->|connectivity failure| Memory
  Router[Central route registration] --> Current[Maintenance / graph / auth / ops / vertical APIs]
  Registry[Domain registry] --> Maintenance[Maintenance sole/default]
```

No startup branch calls seed_demo_data. Retired software routes are absent and
return 404 even if obsolete Gitea settings are true. Explicit graph fixture and
ops-protected manual-reset compatibility is retained; no data purge is part of
this retirement.
