---
id: ctx-scope
title: Domain scope, non-goals, deferred work
status: active
owners: [all]
updated: 2026-10-16
---

# Domain scope and deferred work

## In scope now (product)

- **Maintenance domain only** for Mid-I demos and claims.
- Neo4j-backed `Asset` / `ServiceRecord` graph.
- Diagnostic retrieve → rank → cite → (optional) LLM explanation.
- Existing conflict detection + review queue (preserve; do not rebuild).
- CI (backend tests, frontend tests/build, Docker real-graph smoke).

## Explicitly out of Mid-I product claims

- Software-engineering “decision vault” UX as the product story (legacy code may remain but must not be presented as Halite’s Mid-I feature set).
- MCP product work.
- New PostgreSQL multi-tenant SaaS migration (unless already present and proven).
- Technician Academy, predictive maintenance training, inventory forecasting.
- Full UI redesign that breaks API contracts.
- Silent demo/memory mode while claiming live Neo4j + live LLM.

## Deferred after Mid-I (Umar / team)

| Item | Why deferred |
| --- | --- |
| New trained diagnostic model | Stabilize graph + deterministic ranker first |
| Full vector-index hybrid retrieval (if not already working) | Current POC uses lexical/heuristic similarity; do not over-claim |
| Calibrated fault probabilities | Ranking scores ≠ probabilities |
| Broad component dependency graphs | Causal edges not justified by current data |
| Advanced multi-turn diagnostic session persistence | Vertical slice first |
| Production CD / multi-tenant SaaS hardening | Ops authority + green CI required |
| Fleet-wide service-record search / paginated `GET /maintenance/service-records` | Service Records is per-aircraft for Mid-I; needs a Usman endpoint (see DEC-20261016-service-records-per-aircraft) |
| react-router 7 upgrade | `npm audit` leaves 2 moderate advisories on 6.x whose fix is a breaking major; client-only SPA with fixed `/app/...` link prefixes. Do after Mid-I with full test run |
| vitest 5 upgrade | Dev-only advisories; breaking major |

## Legacy software domain

Code and tests for Decisions/Components still exist for regression. Treat as **frozen infrastructure**, not Mid-I feature work. Historical docs live in `docs/obsolete/`.
