# Usman Mid-I release readiness

Audit date: 2026-10-15<br>
Owner: Muhammad Usman Al Haq<br>
Branch: `usman`<br>
Verified release-evidence SHA: `ecbf1d7cb830648b7f2d78858fb128fa8bd35560`<br>
Current branch tip at repository-hygiene audit start: `b949de47a5c2baadb240cd9d0a1c6c5f8f9b96e9` (README-only commits after the release-evidence baseline)<br>
Latest verified closure run: [`38796169387`](https://github.com/umaritics/halite/actions/runs/38796169387)<br>
Main baseline: `4329556c2405ffa1a397979ae26bc68ad8814eac`

## Release verdict

**Do not integrate yet.** The owned maintenance implementation is tested, but required release proof is incomplete: real FAA data has not been verified in a running isolated Neo4j database; the VM serves an older backend with no maintenance routes; the overall workflow is red on a Shahmeer-owned test; Vercel previews require SSO and have ambiguous ownership; live Groq inference and independent review are unverified.

| Requirement | Status | Proof | Remaining action | Owner |
| --- | --- | --- | --- | --- |
| A1 real FAA corpus in running Neo4j | **BLOCKED** | Ignored CSV inspection proves 2,079 rows, 118 assets, `813SK`, `SWIA2025111676447`, and both `811NN` records. Docker Desktop cannot bootstrap WSL (`0xc00000fd`); no approved alternative corpus host/transfer exists. | Provide isolated Neo4j runtime, temporary credentials, approved private corpus transfer, and authorization to ingest/delete only the isolated database. | Infrastructure administrator + Usman |
| A1 synthetic integration | **PASS** | Docker job `116633015957` on release-evidence SHA `ecbf1d7` passed real-Neo4j fixture ingestion, duplicate safety, health, APIs, frontend serving, logs, and cleanup. | Do not misrepresent this as full FAA proof. | Usman |
| A2 maintenance API/workflow | **PASS** | 59 focused tests passed; complete backend result was 102 passed and 16 explicit Neo4j skips; hosted backend job `116633015975` passed. | None in Usman's owned API scope. | Usman |
| A3 mandatory CI | **FAIL** | On run `38796169387`, backend job `116633015975` and Docker job `116633015957` passed; frontend job `116633015569` failed and skipped the hosted build. | Complete `06_frontend_review_queue_handoff.md`, rerun all jobs, require green overall workflow. | Shahmeer + release coordinator |
| A3 current persistent backend | **FAIL** | `https://dev1.corp.curatech.pk/halite-api/openapi.json` returns 200 through Caddy but exposes 17 paths and zero maintenance paths; maintenance assets returns 404. | Identify/deploy an approved current release SHA and verify health/assets/history. | VM/deployment administrator |
| A3 deployed SHA | **NOT VERIFIED** | Public VM health/OpenAPI exposes no build SHA; server/container access is unavailable. | Provide read-only SSH/container inspection or a `/version` release-metadata mechanism approved by the backend owner. | VM administrator |
| A3 frontend previews | **PARTIAL** | GitHub records two successful Vercel deployments for `fc3db4c`; both URLs redirect unauthenticated checks to Vercel SSO. | Identify the canonical project, grant reviewer access or provide an approved public staging URL, then verify app and `/api` behavior. | Shahmeer/Vercel owner |
| A3 automatic CD | **PARTIAL** | Vercel GitHub App creates preview deployments. Repository CI has no protected backend deploy/promotion/rollback job. | Document Vercel project mapping and add an approved protected backend release process only after credentials/host authority are supplied. | Release coordinator + deployment admin |
| A4 evidence reconciliation | **PASS** | Evidence documents identify latest SHA/run, job-level results, historical runs, and blockers. | Keep final pushed documentation SHA in the PR/reviewer record. | Usman |
| A4 action versions | **PARTIAL** | Current `checkout@v4`, `setup-python@v5`, and `setup-node@v4` execute successfully. Official repositories now publish v7 majors. | Test v7 upgrades in a separate owner-reviewed maintenance change; do not combine three major upgrades with Mid-I closure merely to remove an informational warning. | CI owner |
| Live model | **NOT VERIFIED** | VM says `groq_configured=true`; no successful sanitized diagnostic response was observed. | Umar executes the live-model checklist in `05_usman_final_audit.md`. | Umar |
| Independent review | **NOT VERIFIED** | No reviewer approval or signed verification record exists. | Reviewer reruns gates and records approval/rejection against the final SHA. | Assigned reviewer |

## A1 infrastructure handoff

No safe repair or alternative was available. Read-only checks found both `Ubuntu` and `docker-desktop` WSL distributions stopped, Docker Desktop failing bootstrap with `0xc00000fd`, and no identifiable Neo4j process suitable for isolated use. Restarting WSL, changing the pagefile, downloading a database runtime, transferring ignored FAA files, or writing to the existing demonstration graph requires explicit authority.

Administrator must provide:

1. an isolated Neo4j 5.x database/volume and endpoint, not the existing demonstration database;
2. temporary non-production credentials through an approved secret channel;
3. an approved private transfer path for `sdr_poc_corpus.csv` and `ground_truth_pairs.csv`;
4. permission to ingest twice and remove only the isolated test database/volume afterward;
5. enough runtime access to execute current `usman` backend SHA and retain a sanitized log.

Acceptance commands and assertions are in `docs/mid1_setup.md`. Required runtime evidence is health with `graph_mode=neo4j` and `using_memory_graph=false`, 2,079 records/118 assets (or documented dataset revision), `813SK` history, `SWIA2025111676447`, both ordered/preserved `811NN` records, zero creations on second ingest, and working asset/history/review APIs.

## A3 deployment architecture and handoff

Observed architecture:

- VM definition: `docker-compose.vm.yml`, service `api`, container `halite-api`, host-only `127.0.0.1:8002 -> 8000`.
- Reverse proxy: public headers show `Via: 1.1 Caddy`; repository contains no Caddy configuration.
- Backend URL: `https://dev1.corp.curatech.pk/halite-api/`.
- Expected current endpoints include `/health`, `/api/health`, `/api/maintenance/assets`, `/api/maintenance/assets/{asset_id}/history`, `/api/maintenance/review-queue`, and diagnostic endpoints.
- Actual VM OpenAPI: version `0.1.0`, 17 paths, no maintenance paths. Because OpenAPI and health work through `/halite-api`, the 404 is an old-image/code problem, not an unproven prefix theory.
- Frontend API assumption: `frontend/src/api/client.js` defaults to same-origin `/api`; Vite proxying is development-only. Root `vercel.json` declares frontend/backend services and an `/api` rewrite, but reviewer access is blocked by Vercel SSO.
- Current previews recorded by GitHub: `halite-r82kp5dk5-umaritics-projects.vercel.app` and `halite-pmjd-l1egmi5wp-umaritics-projects.vercel.app`, both successful deployments of `fc3db4c`, neither independently usable without Vercel login.
- Secrets/authority: VM uses server-side `backend/.env`; no approved SSH key, deployment credential, Vercel project authority, or secret-store procedure is present in the repository.

Safe release procedure for the authorized administrator:

1. record current container image ID, deployed Git SHA, environment backup location, and health output;
2. build/tag an immutable backend image from the approved release SHA;
3. preserve the prior tag and current `.env` without printing secrets;
4. deploy with `docker-compose.vm.yml` or the administrator's reviewed equivalent;
5. verify `/health`, `/api/health`, assets, `813SK` history, review queue, and controlled model behavior through Caddy;
6. record the released SHA/image digest;
7. on failure, redeploy the preserved prior image/tag and repeat health checks.

This is a handoff, not evidence that deployment or rollback was executed.

## Ownership and commit provenance

### Usman final verification commits

| Commit | Scope |
| --- | --- |
| `6318300` | CI, Docker/runtime fixture, maintenance validation/tests, setup/evidence, frontend container/build infrastructure. |
| `2651eab` | Runtime-smoke import-path correction. |
| `e569ea8` | Hosted evidence update. |
| `d54d4bd` | Final audit and frontend-owner handoff. |
| `fc3db4c` | Hosted audit-run evidence. |
| `ecbf1d7` | Final release-readiness evidence reconciled to run `38796169387`. |

Two later commits, `6b0b29c` and `b949de4`, modify only `README.md`; they improve project documentation and GitHub Mermaid compatibility and do not change the verified release implementation.

### Inherited cross-owner commits

| Commit | Owner/scope introduced |
| --- | --- |
| `56ff286`, `55deb01`, `ffc0659` | Umar-owned graph implementation changes. |
| `77232c6`, `71c132b`, `ffc0659` | Umar-owned diagnostics route/retrieval changes. |
| `ba61e89`, `77232c6`, `16d6bbe`, `edd7b88`, `ffc0659` | Shahmeer-owned React pages, client adapter, components, and tests. |

No history was rewritten and none of those files was modified during this closure.

## File-by-file branch inventory

Status letters are relative to `origin/main...usman`: `A` added, `M` modified.

### Usman-owned/integration files

```text
A .github/workflows/ci.yml
A backend/agents/maintenance_agent.py
A backend/api/routes/maintenance.py
M backend/main.py
A backend/scripts/verify_mid1_runtime.py
A backend/services/conflict_engine.py
A backend/tests/fixtures/mid1_smoke.csv
A backend/tests/test_api_maintenance.py
A backend/tests/test_conflict_engine.py
A backend/tests/test_maintenance_agent.py
M docker-compose.yml
A docs/mid1/04_data_conflict_devops_evidence.md
A docs/mid1/05_usman_final_audit.md
A docs/mid1/06_frontend_review_queue_handoff.md
A docs/mid1/07_usman_release_readiness.md
A docs/mid1_setup.md
A docs/mid1_test_evidence.md
```

### Shahmeer-owned files requiring Shahmeer review

```text
M frontend/src/App.jsx
M frontend/src/api/client.js
A frontend/src/components/ConfidenceBar.jsx
A frontend/src/components/DomainSwitcher.jsx
M frontend/src/components/GraphViewer.jsx
M frontend/src/components/Sidebar.jsx
A frontend/src/components/StatusChip.jsx
A frontend/src/context/DomainContext.jsx
A frontend/src/pages/AssetHistory.jsx
A frontend/src/pages/Assets.jsx
A frontend/src/pages/Diagnostics.jsx
M frontend/src/pages/Graph.jsx
A frontend/src/pages/MaintenanceIngest.jsx
A frontend/src/pages/ReviewQueue.jsx
A frontend/src/pages/ServiceRecords.jsx
M frontend/src/pages/Settings.jsx
A frontend/src/test/Assets.test.jsx
A frontend/src/test/Diagnostics.test.jsx
A frontend/src/test/DomainContext.test.jsx
A frontend/src/test/MaintenanceIngest.test.jsx
A frontend/src/test/ReviewQueue.test.jsx
A frontend/src/test/ServiceRecords.test.jsx
A frontend/src/test/Sidebar.test.jsx
A frontend/src/test/dummy.test.jsx
A frontend/src/test/setup.js
```

### Umar-owned files requiring Umar review

```text
A backend/api/routes/diagnostics.py
M backend/graph/memory_store.py
M backend/graph/queries.py
M backend/graph/schema.py
A backend/services/diagnostic_retrieval.py
A backend/tests/test_diagnostic_retrieval.py
```

### Shared/historical files requiring release-coordinator review

```text
M .gitignore
M README.md
A backend/.coverage
M backend/.dockerignore
M backend/.env.example
A backend/c3_output.txt
A backend/check_demo_assets.py
A backend/check_groq.py
A backend/check_health.py
M backend/config.py
A backend/data/cache.json
A backend/data/diag_cache/cache.json
A backend/demo_candidate_pairs.py
A backend/docs/misdiagnosis_density.md
A backend/domains/__init__.py
A backend/domains/base.py
A backend/domains/maintenance.py
A backend/domains/registry.py
A backend/domains/software.py
A backend/find_demo_record.py
A backend/gt_results.csv
A backend/neg_results.csv
M backend/requirements.txt
A backend/scripts/__init__.py
A backend/scripts/backfill_conflict_scores.py
A backend/scripts/c4_self_consistency.py
A backend/scripts/check_demo_assets.py
A backend/scripts/d3_latency.py
A backend/scripts/evaluate_conflict_detection.py
A backend/scripts/fetch_sdr_data.py
A backend/scripts/gather_g1_evidence.py
A backend/scripts/measure_misdiagnosis_density.py
A backend/scripts/recalc_baseline.py
A backend/scripts/test_g3_queries.py
M backend/services/groq_service.py
A backend/tests/__init__.py
A backend/tests/conftest.py
A backend/tests/test_graph_maintenance.py
A backend/tests/test_regression_software.py
A backend/top_assets.py
A backend/verify_t6.py
A docs/DATA_LICENCE.md
A docs/DEMO_SCRIPT.md
A docs/dataset_profile.md
A docs/evaluation_results.csv
A docs/evaluation_results.md
A docs/maintenance_architecture.md
A docs/maintenance_handoff.md
A docs/maintenance_state_report.md
A docs/misdiagnosis_density.md
A frontend/.dockerignore
A frontend/Dockerfile
M frontend/package-lock.json
M frontend/package.json
M frontend/vite.config.js
A frontend/vitest.config.js
A halite_check.py
A queue.json
```

The tracked root `vercel.json` already exists on `main` and is not part of this branch diff.

## Contract conflicts and safest integration approach

- Review Queue calls `GET /api/maintenance/records/{id}`; that endpoint performs model-dependent dry-run conflict processing and returns 503 without a live model. Shahmeer's UI/test contract must account for the response shape and unavailable-model state.
- Vercel production uses same-origin `/api` rewrites; Vite proxy settings apply only to the development server. The canonical Vercel project and backend environment must be chosen explicitly.
- The VM health payload is from old code and lacks current corpus/model fields, so HTTP 200 alone is not release readiness.
- Synthetic CI data must remain separate from ignored FAA demonstration data.

The release coordinator should not cherry-pick only the five closure commits: they are evidence for functionality introduced by earlier commits. The safest route is a protected integration PR from `usman` after Shahmeer reviews all frontend paths, Umar reviews diagnostics/graph paths, the coordinator reviews shared artifacts (especially generated caches/results), A1 is executed on isolated infrastructure, staging is updated to a recorded SHA, and the workflow is green. If the coordinator instead creates a clean release branch, ownership-approved commits/files must be selected deliberately and the complete test/real-data/staging gates rerun. Do not rewrite `usman` history and do not merge directly into `main`.
