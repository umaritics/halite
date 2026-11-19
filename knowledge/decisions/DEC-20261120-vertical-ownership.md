---
id: DEC-20261120-vertical-ownership
title: Ownership moves from layers to three full-stack verticals
status: accepted
owners: [Umar, Usman, Shahmeer]
updated: 2026-11-20
---

# DEC-20261120 — Vertical ownership

## Context

Mid-I ownership was by layer: Shahmeer the React pages, Umar the graph and diagnostics internals, Usman the ingest,
conflict engine, CI and wiring. The FYP handbook requires each member to hold a substantial technical responsibility
that includes decisions, implementation and validation, not only UI, and requires ownership changes to be recorded
when they happen. The team also had no single plan for the FYP-I Final.

## Decision

From 20 November 2026 each member owns one sub-problem of the approved complex computing problem end to end:
database, backend, pages, tests, experiment and report chapter.

| Vertical | Owner | Shared duty |
| --- | --- | --- |
| Retrieval and Ranking | Muhammad Umar | Staging VM, deploys, graph backups, corpus builder |
| Record Integrity | Shahmeer Atif | Frontend preparation, app shell and design system, report editing |
| Investigation Sessions | Muhammad Usman Al Haq | Backend preparation, CI quality, Panel Action Register |

Files that change hands:

| Item | From | To |
| --- | --- | --- |
| `services/conflict_engine.py`, `services/conflict_screen.py`, `api/routes/maintenance.py`, `agents/maintenance_agent.py`, analysis scripts | Usman | Shahmeer |
| `scripts/benchmark_local_llm_gt.py` | Umar | Shahmeer |
| `services/groq_service.py` | Umar | Usman |
| `scripts/fetch_sdr_data.py` | Usman | Umar |
| Diagnostics page and its tests | Shahmeer | Usman |
| Knowledge graph page and its tests | Shahmeer | Umar |

The full file map, interfaces and rules are in `docs/plan/CONTRACTS.md`. Each owner's design and work packages are in
`docs/plan/AGENT_GUIDE_<NAME>.md`.

## Consequences

- `knowledge/context/02_ownership_mid1.md` and the owner column of `knowledge/REGISTRY.md` describe Mid-I and are
  historical. Update the registry as each preparation pull request moves files.
- Scope is unchanged: nine modules, thirteen objectives, five research questions.
- Three preparation pull requests (backend, frontend, data) land before parallel work starts.
- The supervisor is told at the next meeting and the agreement is logged in the Panel Action Register.
