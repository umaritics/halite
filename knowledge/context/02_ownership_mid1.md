---
id: ctx-ownership
title: Mid-I ownership and edit rules
status: active
owners: [all]
updated: 2026-10-16
---

# Mid-I ownership

Source: `docs/halite_work_division_mid1.pdf`.

| Member | Owns | Must not edit without handoff |
| --- | --- | --- |
| **Shahmeer** (23I-0711) | React maintenance UX, Axios adapter, Vitest | `backend/**`, Docker, CI workflows |
| **Umar** (23I-0782) | Graph schema/queries, diagnose/chat internals, ranking, citation validation, diagnostic tests | React pages, ingest/review routes, Docker/CI, `main.py` registration |
| **Usman** (23I-0585) | Maintenance APIs, ingest, conflict engine, Compose, CI, setup docs, `main.py` wiring | Diagnostic route internals, graph schema unilateral changes, React pages |

## Feature branches (blueprint)

| Branch | Owner |
| --- | --- |
| `feat/mid1/frontend-diagnostics` | Shahmeer |
| `feat/mid1/graph-diagnostics` | Umar |
| `feat/mid1/maintenance-devops` / `usman` | Usman |

Current Umar working branch: **`feat/mid1/graph-diagnostics`** (from `origin/usman`).

## Umar work packages (checklist)

1. **U1** Audit existing diagnostics (state note + real method labels)
2. **U2** Real-data graph retrieval (Neo4j corpus, bounded, safe empty paths)
3. **U3** Deterministic ranking + provenance
4. **U4** Citation validation + LLM boundary (503 / no invented IDs)
5. **U5** Diagnostic backend tests + handoff fixtures

## Usman packages (for cross-check)

A1 data/env · A2 maintenance APIs/conflict · A3 CI/CD · A4 wiring/docs.  
See [DEC-20261016-usman-baseline.md](../decisions/DEC-20261016-usman-baseline.md).
