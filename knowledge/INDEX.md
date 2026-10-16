---
id: technical-index
title: Topic and path index
status: active
owners: [all]
updated: 2026-10-16
---

# Technical index

Use Ctrl/Cmd+F. Prefer exact code paths when searching.

## Keywords → docs

| Keyword / concept | Document |
| --- | --- |
| Mid-I, vertical slice, acceptance gate | context/00_project_overview.md |
| maintenance-only, software domain dropped | context/01_domain_scope_deferred.md |
| maintenance assets, history, ingest, record counts, N+1 | context/modules/maintenance_api.md, FLOW-ingest.md |
| deferred, vector index, SaaS multi-tenant | context/01_domain_scope_deferred.md |
| Umar, Shahmeer, Usman, ownership | context/02_ownership_mid1.md |
| DomainAdapter, registry | context/03_architecture.md |
| Asset, ServiceRecord, ABOUT, PRECEDED_BY, SUPERSEDES | context/04_data_and_graph.md |
| diagnose, ranked_checks, citation | context/modules/diagnostics.md, modules/diagnostics_u1_audit.md, flows/FLOW-diagnose.md, `services/citation_validation.py`, docs/mid1/08–13 |
| mid1 umar audit, U1–U5 | docs/mid1/08_umar_progress.md (+ 09–13 handoffs) |
| U1 audit, Jaccard, part_name ranker | context/modules/diagnostics_u1_audit.md |
| conflict, needs_review, confidence gate | context/modules/conflict_engine.md, flows/FLOW-conflict-review.md, docs/mid1/16_usman_conflict_score_backfill_handoff.md |
| review queue empty, all confidence 1 | docs/mid1/16_usman_conflict_score_backfill_handoff.md (Usman backfill) |
| ingest, SDR, FAA corpus | flows/FLOW-ingest.md |
| DEMO_MODE, graph_mode, llm_mode | context/modules/devops.md |
| CI, GitHub Actions, docker compose | flows/FLOW-ci.md, context/modules/devops.md |
| staging, remote VM, deploy, OPS_TOKEN, ops/logs | context/modules/remote_backend.md, flows/FLOW-deploy.md |
| Mid-I progress, partner handoff | docs/mid1/README.md, docs/mid1/08_umar_progress.md |
| frontend ECONNREFUSED, VITE_API_URL | docs/mid1/09_frontend_shared_api.md |
| review queue UI | context/modules/frontend.md |
| Usman audit, A1–A4 | decisions/DEC-20261016-usman-baseline.md |

## Code path → docs

| Path | Docs |
| --- | --- |
| `backend/services/diagnostic_retrieval.py` | modules/diagnostics.md, FLOW-diagnose.md |
| `backend/api/routes/diagnostics.py` | modules/diagnostics.md, FLOW-diagnose.md |
| `backend/services/conflict_engine.py` | modules/conflict_engine.md, FLOW-conflict-review.md |
| `backend/api/routes/maintenance.py` | modules/maintenance_api.md, FLOW-ingest.md, FLOW-conflict-review.md |
| `backend/graph/schema.py`, `backend/graph/queries.py` | context/04_data_and_graph.md |
| `backend/agents/maintenance_agent.py` | FLOW-ingest.md |
| `frontend/src/pages/Diagnostics.jsx` | modules/frontend.md, FLOW-diagnose.md |
| `frontend/src/pages/ReviewQueue.jsx` | modules/frontend.md, FLOW-conflict-review.md |
| `.github/workflows/ci.yml` | FLOW-ci.md, modules/devops.md |
| `docker-compose.yml` | modules/devops.md, FLOW-ingest.md |

## Official Mid-I PDFs (repo root of docs/)

| File | Role |
| --- | --- |
| `docs/halite_work_division_mid1.pdf` | Ownership + work packages U1–U5 / A1–A4 / S1–S5 |
| `docs/Halite_FYP_Report.pdf` | Product report / module vision |
| `docs/halite_timeline.pdf` | Milestone percentages |
