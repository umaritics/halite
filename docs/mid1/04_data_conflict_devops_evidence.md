# Muhammad Usman Al Haq — Data, Conflict, Testing and DevOps Evidence

Evidence date: 2026-10-15<br>
Branch under evaluation: `usman`<br>
Baseline commit: `8840c68c32054bf1e9dd1505bbbdef4e22d26f6c`<br>
Scope source: `docs/Halite_FYP1_Mid_Three_Member_Execution_Blueprint.tex`, sections 7.1–7.7<br>
University sources checked: `FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf` and `F26_FYP1_Mid_Report_LaTeX_Complete.pdf`

> Final-audit status (2026-10-15): read this historical implementation record with [`05_usman_final_audit.md`](05_usman_final_audit.md) and [`07_usman_release_readiness.md`](07_usman_release_readiness.md). Latest verified run: [`38794104215`](https://github.com/umaritics/halite/actions/runs/38794104215) at `fc3db4c`. Current verdicts are A1 BLOCKED, A2 PASS, A3 PARTIAL, and A4 PARTIAL. Overall CI remains red, running real-corpus Neo4j proof needs external infrastructure, the VM lacks current maintenance routes, live-model success is not verified, and independent review is pending.

## Verification standard

An item is marked **Verified** only when an executed command, test, or inspectable source file supports it. **Remote pending** means the implementation exists locally but requires a hosted GitHub Actions result. **Blocked** records a real failure and is not counted as completed. No result below is inferred from generated code alone.

The official Mid-I rubric specifically expects a working core module with failure cases, systematic executed tests, repository/member evidence, reproducible setup, implementation documentation, and transparent dependency/tool/risk disclosure. This evidence file maps those expectations to Usman's owned work.

## Executive result

| Area | Status | Proof |
| --- | --- | --- |
| Branch isolation | **Verified** | `git branch -vv` showed `usman` at baseline and `main` remained at `4329556`; no merge was performed |
| Maintenance API safety | **Verified** | 59/59 focused tests passed locally |
| Complete backend regression suite | **Verified** | 102 passed, 16 explicit Neo4j skips in a CI-equivalent no-Neo4j environment |
| Frontend production build | **Verified** | Vite build passed; 857 modules transformed |
| Frontend tests | **Blocked outside Usman ownership** | 12 passed, 1 failed because `ReviewQueue.test.jsx` omits the existing `maintenanceAPI.getRecord` mock |
| Compose structure | **Verified** | `docker compose config --quiet` passed |
| Local full Docker runtime | **Blocked by host** | Docker Desktop failed under the Windows paging-file/WSL engine condition; see `docs/mid1_test_evidence.md` |
| Hosted Docker runtime | **Verified** | Docker job `116587631664` built images, started all services, verified real Neo4j/corpus/API behavior, served the frontend, and cleaned up successfully |
| Hosted GitHub Actions URL | **Captured; overall red on cross-owner frontend test** | <https://github.com/umaritics/halite/actions/runs/38782968975> |
| Secrets/data protection | **Verified** | `.env`, raw FAA data, and processed FAA data are ignored; `backend/.env` is absent from Git object history |

## A1 — Data and environment baseline

| Required point | Status | Evidence and proof |
| --- | --- | --- |
| Read handoff/state/Compose/environment docs | **Verified** | Audited `README.md`, `docs/maintenance_handoff.md`, `docs/maintenance_state_report.md`, `docker-compose.yml`, and `backend/.env.example` |
| Docker uses real Neo4j with `DEMO_MODE=false` | **Verified remotely** | Compose overrides `NEO4J_URI=bolt://neo4j:7687` and `DEMO_MODE=false`; hosted smoke passed assertions for `graph_mode=neo4j`, `using_memory_graph=false`, and `demo_mode=false` |
| Health records graph/corpus/model mode | **Verified remotely** | `/api/health` exposed the required fields; hosted smoke verified Neo4j mode and a loaded non-zero corpus while preserving fallback model disclosure |
| Identify safe import command | **Verified** | `POST /api/maintenance/ingest` loads `data/processed/sdr_poc_corpus.csv`; second import is verified idempotent in unit tests and remote smoke |
| Select a real deterministic asset | **Verified against local FAA corpus** | Local ignored corpus has 2,079 rows and 118 assets; asset `813SK` has 153 records. Example record: `SWIA2025111676447` |
| Select a real conflict case | **Verified against local ground truth** | 141 ground-truth pairs exist. Deterministic example: `AALA202501025620` → `AALA202501035620`, tail `811NN` |
| Protect credentials and downloaded data | **Verified** | `git check-ignore -v` confirms rules for `backend/.env`, `backend/data/raw/`, and `backend/data/processed/`; history lookup returned no tracked `backend/.env` object |

Commands executed:

```text
git check-ignore -v backend/.env backend/data/raw backend/data/processed
git rev-list --objects --all | Select-String '(^|/)backend/\.env$'
python -c "... read sdr_poc_corpus.csv and ground_truth_pairs.csv ..."
```

Observed corpus proof:

```json
{
  "corpus_rows": 2079,
  "asset_count": 118,
  "demo_asset": "813SK",
  "demo_asset_record_count": 153,
  "demo_record_id": "SWIA2025111676447",
  "ground_truth_pair_count": 141,
  "conflict_example": {
    "superseded_record_id": "AALA202501025620",
    "superseding_record_id": "AALA202501035620",
    "tail_number": "811NN"
  }
}
```

## A2 — Maintenance APIs and conflict workflow

| Required behavior | Automated proof |
| --- | --- |
| Empty asset list and unknown asset handling | `TestAssetsEmpty` verifies empty list and controlled 404 |
| Asset list and record counts | `test_assets_listed_after_seed` |
| Chronological asset history | `test_asset_history_returned` |
| Review queue filters `needs_review` | `test_review_queue_returns_needs_review` |
| Accept review state | `test_accept_changes_status` |
| Reject requires a meaningful note | `test_reject_requires_note` and `test_reject_disallows_blank_note` |
| Reject preserves the original record | `test_reject_with_note_succeeds` checks record ID and text |
| Completed review cannot be overwritten | `test_reject_cannot_overwrite_completed_review` expects HTTP 409 |
| Invalid ingest limit and threshold | 422 tests for non-positive limit and threshold outside `[0,1]` |
| Duplicate ingestion | `test_idempotent_second_run` plus hosted Docker smoke second-ingest assertion |
| Conflict candidate scope/routing/failure guard | `test_conflict_engine.py` covers same-asset filtering, max candidates, chronology, classification labels, confidence boundaries, conservative review routing, and unavailable-model guard |
| Agent ingestion quality | `test_maintenance_agent.py` covers blank tails, invalid dates, missing IDs, duplicates, ordering, mixed rows, and empty input |

Focused execution:

```text
python -m pytest -q tests/test_api_maintenance.py tests/test_conflict_engine.py tests/test_maintenance_agent.py
59 passed in 0.64s
```

The hosted Docker smoke uses only `backend/tests/fixtures/mid1_smoke.csv`. It verifies first ingest, duplicate-safe second ingest, real Neo4j health, assets, history, review queue, accept, reject, original-record preservation, transparent HTTP 503 when the live model is unavailable, and HTTP 404 for an unknown asset. It does not modify the real FAA demo corpus.

## A3 — GitHub Actions and repository health

Workflow: `.github/workflows/ci.yml`

| Hosted job | What it proves | Failure policy |
| --- | --- | --- |
| Backend tests | Python 3.11 dependency install and complete `pytest -q` | Any failed test fails the job |
| Frontend tests/build | Node 20, clean `npm ci`, Vitest, and Vite production build | Tests are not skipped or masked |
| Docker real-graph smoke | Compose render, image builds, full stack startup, Neo4j-mode health, ingestion, asset/history/review APIs, frontend HTTP response | Any build, health, assertion, or HTTP failure fails the job; logs are captured with `if: always()` |

The Docker job deletes only its ephemeral GitHub runner volume after capturing logs. The setup guide explicitly warns against `docker compose down -v` on the team's persistent demo corpus.

Remote evidence from the latest run:

```text
Commit SHA: 2651eab580c2c3e46069dec1a5c1364f8fafb95b
Workflow URL: https://github.com/umaritics/halite/actions/runs/38782968975
Backend job: SUCCESS
  https://github.com/umaritics/halite/actions/runs/38782968975/job/116587631265
Frontend job: FAILURE on Shahmeer's stale ReviewQueue mock
  https://github.com/umaritics/halite/actions/runs/38782968975/job/116587632014
Docker smoke job: SUCCESS
  https://github.com/umaritics/halite/actions/runs/38782968975/job/116587631664
```

The Docker job independently passed all of these hosted steps: Compose render, backend/frontend image builds, full-stack startup, backend health wait, real Neo4j/corpus/API verification, frontend HTTP verification, log capture, and ephemeral cleanup. The overall workflow conclusion remains red only because the independent frontend test job failed; this is not represented as a fully green workflow.

## A4 — Backend wiring and documentation

| Deliverable | Status | Path/evidence |
| --- | --- | --- |
| Router/health wiring | **Verified** | `backend/main.py` registers maintenance, diagnostics, and domains routers and exposes both health paths |
| Maintenance-focused README | **Verified** | `README.md` now describes the Mid-I workflow, Docker endpoints, ingestion, and failure-safe demo flow |
| Reproducible setup manual | **Verified** | `docs/mid1_setup.md` includes requirements, safe variables, Docker and host startup, ingestion, health assertions, tests, diagram, and troubleshooting |
| Exact test/result log | **Verified locally and job-level remote evidence recorded** | `docs/mid1_test_evidence.md` and `docs/mid1/05_usman_final_audit.md`; the mandatory overall workflow remains red |
| Runtime/deployment diagram | **Verified** | Mermaid dependency diagram in `docs/mid1_setup.md` |
| Deterministic container install | **Verified in source and hosted Docker build** | Backend pins Python requirements; frontend Dockerfile uses lockfile-backed `npm ci`; hosted Docker job `116589585728` passed |

## Complete local command log

| Command | Result |
| --- | --- |
| `python -m py_compile scripts/verify_mid1_runtime.py` | PASS |
| Focused Usman PyTest command | PASS — 59 tests |
| CI-equivalent complete backend PyTest | PASS — 102 passed, 16 explicit Neo4j skips |
| `npm test -- --run` | FAIL — 12 passed, 1 Shahmeer-owned stale mock failure |
| `npm run build` | PASS — 857 modules transformed |
| `docker compose config --quiet` | PASS |
| `docker compose up --build -d` | BLOCKED locally by Windows paging-file exhaustion |
| `docker compose up -d neo4j` retry | BLOCKED locally by Docker Desktop WSL bootstrap error `0xc00000fd` |
| `git diff --check` | PASS |

## Cross-owner blocker — not hidden

`frontend/src/pages/ReviewQueue.jsx` calls the existing `maintenanceAPI.getRecord` method. `frontend/src/test/ReviewQueue.test.jsx` replaces the entire API object but does not provide a `getRecord` mock, causing `TypeError: maintenanceAPI.getRecord is not a function`. Fixing that frontend test belongs to Shahmeer under the agreed ownership rules. Usman's CI correctly exposes the failure rather than excluding the test.

Required frontend-owner action:

1. Add `getRecord: vi.fn()` to the mocked `maintenanceAPI`.
2. Return the record-detail response shape expected by `ReviewQueue.jsx`.
3. Run the complete Vitest suite and build.
4. Re-run the hosted workflow and record the green URL here.

## Threshold, accuracy and model disclosures

- No confidence threshold was changed to improve demo appearance.
- The existing conflict evaluation used a small sample and must not be presented as independently validated diagnostic accuracy.
- The historical G0 negative result remains preserved; broad component-dependency mining is not claimed.
- `llm_mode=fallback` is disclosed as unavailable live inference. The remote smoke expects the model-dependent record-detail call to return a transparent 503 when no key is supplied.
- The synthetic remote smoke fixture proves integration behavior, not FAA dataset accuracy. Real-data claims above come from the locally present ignored FAA corpus and must be rechecked on the final demonstration database.

## Final Usman checklist

- [x] Real local corpus files inspected; real asset and conflict IDs recorded.
- [x] Asset/history/record/review API tests executed.
- [x] Duplicate, invalid-input, unknown-asset, and model-unavailable paths covered.
- [x] Accept/reject semantics preserve original record fields and prevent review overwrite.
- [x] GitHub workflow installs dependencies and runs real tests/builds without masking failures.
- [x] Docker images and full real-Neo4j runtime are exercised by hosted smoke automation.
- [x] Setup, health interpretation, ingestion, deployment diagram, and limitations documented.
- [x] Secrets and downloaded datasets excluded from Git.
- [x] Hosted workflow and individual job URLs captured.
- [x] Docker smoke job observed green on GitHub.
- [ ] Frontend owner resolves the one stale test mock and complete workflow becomes green.
- [ ] Final demo database health shows `graph_mode=neo4j` and a non-zero real FAA corpus.
- [ ] Independent reviewer and PR evidence recorded.

## Reviewer verification commands

```bash
git switch usman
git status --short --branch

cd backend
python -m pip install -r requirements.txt
python -m pytest -q

cd ../frontend
npm ci
npm test
npm run build

cd ..
docker compose config --quiet
docker compose up --build -d
docker compose exec -T backend python scripts/verify_mid1_runtime.py
docker compose ps
```

Expected success marker from the container integration proof:

```text
MID1_RUNTIME_SMOKE=PASS
```

Do not merge this branch into `main` until the hosted run, reviewer check, and remaining unchecked items are completed.
