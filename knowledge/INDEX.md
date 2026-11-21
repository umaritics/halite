---
id: technical-index
title: Topic and path index
status: active
owners: [all]
updated: 2026-10-25
---

# Technical index

Use Ctrl/Cmd+F. Prefer exact code paths when searching.

## Keywords → docs

| Keyword / concept | Document |
| --- | --- |
| Sentence grounding, L2/L3, blinded labels, Cohen kappa, threshold proposal | context/modules/investigation_grounding.md, flows/FLOW-grounding.md, docs/work/usman/grounding_review_v1/README.md |
| Model comparison, Ollama, M4, no-evidence baseline, resumable measurements | context/modules/investigation_model_comparison.md, flows/FLOW-model-comparison.md, docs/work/usman/MODEL_COMPARISON_RUNNER.md |
| Mid-I, vertical slice, acceptance gate | context/00_project_overview.md |
| maintenance-only, software domain dropped | context/01_domain_scope_deferred.md |
| maintenance assets, history, ingest, record counts, N+1 | context/modules/maintenance_api.md, FLOW-ingest.md |
| deferred, vector index, SaaS multi-tenant | context/01_domain_scope_deferred.md |
| Umar, Shahmeer, Usman, ownership | context/02_ownership_mid1.md |
| DomainAdapter, registry | context/03_architecture.md |
| Asset, ServiceRecord, ABOUT, PRECEDED_BY, SUPERSEDES | context/04_data_and_graph.md |
| diagnose, copilot, multi-turn, case_state, ranked_checks, citation | context/modules/diagnostics.md, modules/diagnostics_u1_audit.md, flows/FLOW-diagnose.md, `services/citation_validation.py`, docs/mid1/08–13, docs/mid1/17_diagnostic_copilot_evidence.md |
| diagnostic evidence, provenance, same aircraft, fleet evidence, evidence grouping | context/modules/frontend.md, context/modules/diagnostics.md, flows/FLOW-diagnose.md, decisions/DEC-20261025-evidence-provenance.md |
| mid1 umar audit, U1–U5 | docs/mid1/08_umar_progress.md (+ 09–13 handoffs) |
| U1 audit, Jaccard, part_name ranker | context/modules/diagnostics_u1_audit.md |
| conflict, analysis_state, unscored, needs_review, confidence gate, cascade, daily budget, migration | context/modules/conflict_engine.md, flows/FLOW-conflict-review.md, decisions/DEC-20261017-conflict-analysis-state.md, decisions/DEC-20261017-analysis-cost-cascade.md, docs/mid1/19_confidence_and_corrections_evidence.md, docs/mid1/21_analysis_cascade_evidence.md |
| review queue empty, all confidence 1, legacy placeholder | decisions/DEC-20261017-conflict-analysis-state.md, docs/mid1/19_confidence_and_corrections_evidence.md |
| ingest, SDR, FAA corpus | flows/FLOW-ingest.md, decisions/DEC-20261017-ingest-csv-upload-ui.md |
| DEMO_MODE, graph_mode, llm_mode | context/modules/devops.md |
| CI, GitHub Actions, docker compose | flows/FLOW-ci.md, context/modules/devops.md |
| staging, remote VM, deploy, OPS_TOKEN, ops/logs | context/modules/remote_backend.md, flows/FLOW-deploy.md |
| local LLM, Ollama, OPENAI_COMPAT, conflict backfill | docs/local-llm-staging.md, docs/mid1/25_local_llm_staging_evidence.md, decisions/DEC-20261115-local-ollama-staging.md, decisions/DEC-20261116-staging-corpus-analysis-complete.md, docker-compose.vm.yml |
| corpus analysis complete, 0 unscored, review queue bulk | decisions/DEC-20261116-staging-corpus-analysis-complete.md, docs/mid1/25_local_llm_staging_evidence.md |
| security, HALITE_API_KEY, Bearer auth, rate limit, EXPOSE_OPENAPI, Gitea 410 | docs/security-public-deployment.md, decisions/DEC-20261114-public-api-security-hardening.md, `backend/api/security.py`, `backend/api/router.py` |
| login, RBAC, Argon2, JWT, invite, PostgreSQL, audit_events, reviewed_by, TeamAccess | decisions/DEC-20261114-workspace-auth-rbac-postgresql.md, docs/security-public-deployment.md, `backend/db/models/identity.py`, `backend/services/auth_service.py`, `backend/api/routes/auth.py`, `frontend/src/context/AuthContext.jsx` |
| Mid-I progress, partner handoff | docs/mid1/README.md, docs/mid1/08_umar_progress.md |
| frontend ECONNREFUSED, VITE_API_URL | docs/mid1/09_frontend_shared_api.md |
| review queue UI, accept/reject, stored finding | context/modules/frontend.md, decisions/DEC-20261016-review-actions-server-confirmed.md |
| service records, fleet-wide, corrections, pagination, fan-out | decisions/DEC-20261017-fleet-service-records.md, modules/maintenance_api.md, docs/mid1/19_confidence_and_corrections_evidence.md |
| graph reset, destructive endpoint, ops token, `.env.local` | decisions/DEC-20261018-protect-graph-reset.md, modules/devops.md |
| knowledge graph page, graph limit, aircraft focus, SUPERSEDES styling | decisions/DEC-20261017-graph-aircraft-focus.md, modules/frontend.md |
| frontend shows backend fields (rank score, confidence, JASC, health flags), never hides | decisions/DEC-20261016-frontend-reflects-backend-outputs.md |
| legacy software UI, domain lock, Settings reset removed | decisions/DEC-20261016-frontend-maintenance-only.md |
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
| `frontend/src/components/DiagnosticEvidenceInspector.jsx`, `frontend/src/utils/diagnosticEvidence.js` | modules/frontend.md, FLOW-diagnose.md, decisions/DEC-20261025-evidence-provenance.md |
| `frontend/src/pages/MaintenanceIngest.jsx`, `frontend/src/components/CsvUploader.jsx`, `frontend/src/components/IngestResult.jsx` | modules/frontend.md, flows/FLOW-ingest.md, decisions/DEC-20261017-ingest-csv-upload-ui.md |
| `frontend/src/pages/Graph.jsx`, `frontend/src/utils/graphScope.js`, `frontend/src/components/GraphViewer.jsx` | modules/frontend.md, decisions/DEC-20261017-graph-aircraft-focus.md |
| `frontend/src/pages/ReviewQueue.jsx`, `frontend/src/pages/ServiceRecords.jsx` | modules/frontend.md, FLOW-conflict-review.md, decisions/DEC-20261017-fleet-service-records.md |
| `.github/workflows/ci.yml` | FLOW-ci.md, modules/devops.md |
| `docker-compose.yml` | modules/devops.md, FLOW-ingest.md |

## Official Mid-I PDFs (repo root of docs/)

| File | Role |
| --- | --- |
| `docs/halite_work_division_mid1.pdf` | Ownership + work packages U1–U5 / A1–A4 / S1–S5 |
| `docs/Halite_FYP_Report.pdf` | Product report / module vision |
| `docs/halite_timeline.pdf` | Milestone percentages |

## Backend preparation

`graph/repo/`, `graph/memory/`, `db/models/`, vertical summary routes and model `json_mode`:
see `decisions/DEC-20261120-backend-foundation.md`, `context/modules/backend_foundation.md`,
`flows/FLOW-backend-foundation.md` and `docs/work/usman/WORK_LOG.md`.

Persisted sessions, replay, owner/organisation access, degraded diagnosis, cache
invalidation: `context/modules/investigation_sessions.md`, `flows/FLOW-sessions.md`,
`decisions/DEC-20261120-durable-investigations.md`, `backend/investigation/`.
CI lint/coverage and Form 10: `context/modules/devops.md`, `flows/FLOW-ci.md`,
`docs/fyp1-final/PANEL_ACTION_REGISTER.md`.

Investigation history/resume/close/print, home widgets, frontend identity isolation:
`context/modules/investigation_frontend.md`, `frontend/src/features/investigation/`,
`frontend/src/features/home/`, `docs/work/usman/FRONTEND_INTEGRATION.md`.

Beliefs/entropy/other bucket, answer/ask/abstain, 2023 fit/2024 selection, temporal isolation:
`context/modules/investigation_decisions.md`, `flows/FLOW-decision-selection.md`,
`decisions/DEC-20261120-decision-core-protocol.md`, `backend/investigation/experiments/`.

## Question selection (Usman)

`backend/investigation/{attributes,questions}.py`, `experiments/{temporal_questions,simulated_technician,import_faa_codes}.py`, `data/faa_codes.json`, `params/report-attributes-v1.json`: [context](context/modules/investigation_questions.md), [flow](flows/FLOW-question-selection.md). Offline core verified; live questions and shared ingest integration remain separate.

Managed questions (Usman): `backend/investigation/{live_graph,live_questions}.py`, session service/API, `SESSION_*` settings; [context](context/modules/investigation_live_questions.md), [flow](flows/FLOW-live-questions.md). UI: `DecisionView.jsx`; real browser: `frontend/e2e/verify-question-ui.cjs`.

Research publication (Usman): `backend/investigation/research_results.py`, `experiments/results/publication.json`, sessions experiments route and `tests/test_research_results*.py`; [context](context/modules/investigation_decisions.md), [flow](flows/FLOW-decision-selection.md).

Research product panel (Usman): `frontend/src/features/investigation/{ResearchPage.jsx,research.js}`, `frontend/e2e/verify-research-ui.cjs`; [context](context/modules/investigation_frontend.md), [flow](flows/FLOW-research-publication.md). Hosted browser verification is part of CI; owner review/merge remain separate.

Source-word interaction (Usman): `backend/investigation/grounding.py::source_matches`, `frontend/src/features/investigation/SourceNarrative.jsx`, sentence callbacks in DecisionView and source selection in quick/session pages. [Context](context/modules/investigation_grounding.md), [flow](flows/FLOW-grounding.md), [decision](decisions/DEC-20261121-saved-source-word-spans.md).

Dependency resolution evidence (Usman): `backend/requirements*.txt`, `.github/workflows/ci.yml`, `docs/work/usman/verify_dependency_cleanup.py`, `backend/tests/test_settings_env_file.py`; [decision](decisions/DEC-20261121-dependency-cleanup.md), [CI context](context/modules/devops.md). Separate legacy retirement authorization/proposal: `docs/work/usman/LEGACY_RETIREMENT_HANDOFF.md`.

| legacy retirement, 404, no startup seed | decisions/DEC-20261121-legacy-retirement.md; docs/work/usman/LEGACY_RETIREMENT_HANDOFF.md |

| exact coverage gate, artifact provenance tests | decisions/DEC-20261121-research-tool-verification.md; backend/tests/test_research_artifact_tools.py |

| question-conditioned policy selection, stopping prefixes | decisions/DEC-20261121-question-conditioned-selection.md; investigation/experiments/policy_selection.py |

| selected .80/.50 policy, held-out preflight, label availability | decisions/DEC-20261121-frozen-research-point.md; investigation/experiments/frozen_policy.py; docs/fyp1-final/OPERATING_POINT_DECISION.md |

| reproduce fit/selection label timing | docs/work/usman/audit_label_availability.py; evidence/phase16-frozen-policy/label-availability-audit.json |

| held-out 2025 execution, ECE, fixed terminal counterfactual | investigation/experiments/held_out.py; docs/work/usman/verify_held_out.py; decisions/DEC-20261121-held-out-procedure.md |
