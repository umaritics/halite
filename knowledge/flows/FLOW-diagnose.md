---
id: flow-diagnose
title: Diagnostic investigation flow
status: active
owners: [Umar, Shahmeer]
updated: 2026-10-16
---

# FLOW-diagnose — symptom to ranked checks

## Actors

Technician (UI) → Frontend → `POST /api/maintenance/diagnose` → retrieval + rank → citation validate → optional LLM explain → UI renders `ranked_checks`.

## Happy path

1. User selects asset from `/api/maintenance/assets` (real corpus ID).
2. Opens Diagnostics; enters symptom text.
3. UI calls `maintenanceAPI.diagnose(assetId, symptomText)`.
4. Backend loads/builds diagnostic context from Neo4j (bounded history + similar records).
5. Ranker orders investigative checks with evidence record IDs.
6. LLM (or cache) produces explanation constrained to retrieved IDs.
7. `_validate_citations` confirms/flags IDs.
8. UI shows ranked list, explanation, warnings, citation status; user opens a cited record.

## Failure modes

| Case | Expected |
| --- | --- |
| Unknown asset | Controlled 404 / empty — no invented history |
| No relevant history | Empty/low ranked checks; no fabricated repair |
| Groq down, no cache | HTTP 503 with clear message |
| Model invents ID | Citation validator rejects/flags |

## Dependency graph

```mermaid
flowchart TB
  subgraph frontend
    D[Diagnostics.jsx]
    C[api/client.js maintenanceAPI.diagnose]
    H[AssetHistory / ServiceRecords]
  end
  subgraph backend
    R[api/routes/diagnostics.py]
    RET[services/diagnostic_retrieval.py]
    G[services/groq_service.py]
    CACHE[data/diag_cache/cache.json]
    QR[graph/queries.py GraphRepository]
  end
  subgraph data
    N[(Neo4j Asset/ServiceRecord)]
  end
  D --> C --> R
  R --> RET
  R --> G
  R --> CACHE
  RET --> QR --> N
  D -. opens evidence .-> H
```

## File dependencies (edges)

- `Diagnostics.jsx` → `client.js` → `diagnostics.py`
- `diagnostics.py` → `diagnostic_retrieval.py` → `queries.py` → Neo4j
- `diagnostics.py` → `groq_service.py` + diag cache
- UI evidence click → history/record routes (`maintenance.py`)
