# Muhammad Usman Al Haq FYP I final work log

## Scope and source priority

The user's request authorizes completing Usman's FYP-I final responsibilities carefully, one complete phase at a time, with evidence. The supplied master plan is the planning priority; dates do not constrain execution. Document instructions are project guidance, not independent authorization to contact teammates, change staging, invent human reviews, labels or approvals.

Read: supplied `Halite_Master_Plan.docx`, repository `AGENTS.md`, knowledge router and decisions, `docs/plan/CONTRACTS.md`, `docs/plan/AGENT_GUIDE_USMAN.md`, architecture, maintenance, CI and diagnostic context/flows. The proposal is supplementary background, not a replacement for the master plan.

## Repository state and preservation

- Fetched origin successfully. Latest main: `0dd86d9` (master-plan merge).
- Original checkout: `feat/copilot-ranking-updates`, two commits ahead and twenty behind main, with pre-existing edits to `knowledge/REGISTRY.md`, `knowledge/context/modules/frontend.md`, `vercel.json`, an untracked routing test and an untracked ZIP. None modified by this work.
- Isolated worktree (initially `/tmp/halite-usman-phase1`, moved after verification to the permanent project folder `.worktrees/usman-phase1`), branch `codex/usman-phase1`, based on latest main. No reset, stash or overwrite of original work.

## Phase 1 acceptance boundary

Complete the compatibility-preserving backend foundation (WP-S0 steps 2–5) and the adapter's JSON/prose contract (the adapter subset of WP-S1):

- Split graph repository and memory implementation into vertical mixins without changing method bodies, names, signatures or existing imports.
- Split relational models into an identity module and imported extension modules without changing identity tables.
- Register retrieval, evaluation, integrity and sessions routers once, under existing authentication; provide empty summary responses without fabricated statistics.
- Add marked settings blocks, retaining the current heuristic as default.
- Prose model calls omit JSON response format; JSON extraction explicitly requests it, including usage-aware calls and provider retry.
- Existing maintenance, security, identity, retrieval and conflict behavior stays unchanged; add meaningful tests for the new contracts. The one pre-existing failing assertion is corrected by its owner-authored upstream commit (recorded below).
- Update knowledge and capture actual command results.

Legacy removal is a separate compatibility change, not completed in this phase. The plan's instruction to delete the software domain conflicts with unchanged maintenance tests: `test_api_maintenance.py` explicitly requires software to remain the default registered domain. The existing graph route also consumes legacy methods and security tests cover retired Gitea routes. Legacy methods are isolated in `legacy.py` so the next cleanup can remove them with explicit contract/test updates; they are not mixed into the new vertical files. WP-S0 as a whole stays open until cleanup is resolved; this phase does not claim it complete.

## Subsequent phases

1. Backend foundation and JSON/prose adapter contract — current phase.
2. Resolve legacy retirement contract; CI lint/coverage and Panel Action Register (WP-S0 remainder, WP-S11).
3. Persisted sessions, access controls, degraded turns/cache correctness (WP-S1 remainder, WP-S2).
4. Session history/workspace after shared frontend preparation (WP-S3).
5. Beliefs/policy, leakage-safe experiments, question selection and coded fields (WP-S4/S5).
6. Grounding, home dashboard and model comparison harness (WP-S6/S7/S10).
7. Should-tier judge/annotation tooling and printable reports (WP-S8/S9), integration and final evidence.

Human decisions and genuine empirical results remain explicit: no invented feedback, FAA meanings, model comparisons, labels, calibration results, reviewer signatures or live-service claims.

## Evidence

Verification output is stored in `evidence/` alongside this log. Results will be added after execution, including failures and their resolution.

## AI assistance disclosure

Codex read the plan and repository, prepared the code changes, automated checks and engineering documentation. No human review, student-authored design note, manual label or supervisor approval is claimed.

### Upstream baseline repair

Latest main initially produced **1 failed, 217 passed, 23 skipped**. The sole failure was `test_analysis_run_requires_token_and_live_llm`: the assertion said `live Groq`, while production correctly reports `live LLM`. Shahmeer's existing remote fix `797778a` on `origin/fix/integrity/analysis-run-llm-message` was incorporated as `4ce566c`. It changes only that assertion and its explanatory comment. No maintenance production behavior was changed. Baseline output is retained in `evidence/baseline-tests.txt`.

### Environment recovery

The sandbox blocked Git metadata writes and external dependency downloads; authorized escalated commands resolved those. Sandbox API-client runs stalled and were interrupted; equivalent tests completed outside the sandbox. The first image pull timed out and a retry succeeded. Disk exhaustion interrupted Neo4j initial-password setup; clearing the re-downloadable pip cache recovered space and restarting the disposable database returned a successful real Cypher query. No existing containers, data volumes or project files were removed.

## Phase 1 result — complete within the acceptance boundary

### Implementation inventory

- `backend/graph/repo/{core,retrieval,integrity,legacy,_helpers}.py` and package export: all 43 original repository methods preserved.
- `backend/graph/memory/{core,retrieval,integrity,legacy,_helpers}.py` and export: all 53 memory methods preserved.
- `backend/graph/{queries,memory_store}.py`: compatible import facades.
- `backend/db/models/identity.py`: byte-identical five-table identity implementation; package registry imports evaluation/integrity/session extension modules.
- Four `backend/api/routes/{retrieval,evaluation,integrity,sessions}.py` routers registered in the authenticated parent in `api/router.py`. Empty `stats` lists, no fabricated totals.
- `backend/config.py` and `backend/.env.example`: marked settings blocks; `RETRIEVAL_MODE=mid_heuristic`, with no ranker change.
- `backend/services/groq_service.py`: explicit JSON mode on both providers, both extraction methods and usage/key-retry paths.
- `backend/api/routes/diagnostics.py`: the two structured callers (fact extraction and quick-diagnose explanation) explicitly retain JSON mode; conversational replies use prose. No response field changed.
- `backend/tests/test_backend_preparation.py` and `test_model_adapter_format.py`: 18 new contract tests.

### Executed verification

| Check | Actual result | Evidence |
| --- | --- | --- |
| Pre-change main backend suite | 1 known failure, 217 passed, 23 skipped; repaired with Shahmeer's existing commit | `evidence/baseline-tests.txt` |
| Final full backend suite with disposable Neo4j | **259 passed, zero failed, zero skipped** | `evidence/backend-tests-neo4j.txt` |
| Frontend test suite | **223 passed in 21 files** | `evidence/frontend-tests.txt` |
| Frontend production build | **PASS**, with the existing large-chunk advisory | `evidence/frontend-build.txt` |
| Production startup and repository smoke script, real Neo4j + PostgreSQL | **MID1_RUNTIME_SMOKE=PASS** | `evidence/runtime-smoke.txt`, `evidence/runtime-server.txt` |
| Graph method bodies/signatures | **96 of 96 identical** to main baseline | `evidence/refactor-equivalence.json` |
| Identity model source | **Byte-identical** to baseline | `evidence/refactor-equivalence.json` |
| Existing tests | No unexpected modifications; only owner-authored upstream provider-name fix | `evidence/refactor-equivalence.json` |
| Syntax and whitespace checks | `compileall` and `git diff --check` pass | executed during final review |

The full backend command, from `backend/`, used the isolated test database only:

```bash
DEMO_MODE=true NEO4J_URI=bolt://127.0.0.1:17687 NEO4J_USERNAME=neo4j \
NEO4J_PASSWORD=phase1-test-password /tmp/halite-phase1-venv/bin/python -m pytest -q \
  --cov=graph --cov=db --cov=services.groq_service \
  --cov=api.routes.retrieval --cov=api.routes.evaluation \
  --cov=api.routes.integrity --cov=api.routes.sessions \
  --cov-report=term-missing --cov-report=xml:../docs/work/usman/evidence/backend-coverage.xml
```

Dependency versions are captured in `evidence/python-dependencies.txt`. Verification ran on Python 3.12 locally; the existing CI uses Python 3.11. No remote CI run or staging deployment is claimed. The measured-module coverage is 70.57% including legacy; summary routes and identity models are 100%, model adapter 85%. This diagnostic measurement is recorded honestly; WP-S11 still owns CI quality and the 80% target.

The runtime smoke verified unauthenticated 401, PostgreSQL sign-in/invite acceptance, technician review denial (403), admin acceptance with reviewer identity, CSV creation and duplicate-safe re-ingest, asset/history reads, review rejection, unavailable-model 503 and unknown-asset 404. `/api/health` reported `graph_mode=neo4j`, `auth_db_mode=postgresql`, `demo_mode=false`, `llm_mode=fallback`; after ingest it reported three synthetic maintenance records. No live-model claim is made. The script cleaned its synthetic records. The disposable databases and temporary server are stopped/removed after verification; no shared staging data was accessed.

### Knowledge bank and reproducibility

Updated architecture, registry, index, router, maintenance context, ingest and diagnostic flows. Added `context/modules/backend_foundation.md`, `flows/FLOW-backend-foundation.md` and `decisions/DEC-20261120-backend-foundation.md` with an index row.

Run `python3 docs/work/usman/verify_refactor.py` from this checkout to reproduce the structural comparison against main `0dd86d9` and Shahmeer's fix `797778a`.

### Remaining work is explicitly outside phase 1

Phase 1 does **not** claim all FYP-I work, all WP-S0, all WP-S1, a completed session product, a live language model or a passing remote CI workflow. The subsequent-phase list above remains the execution queue. Backend legacy retirement needs the recorded compatibility conflict resolved; the master plan's student design note, labels, model selection and operating-point decisions remain genuine human contributions.

## Phase 2 — durable sessions, degraded diagnosis and CI reports

Branch: `codex/usman-sessions`, stacked on `codex/usman-phase1` in the same permanent worktree. The preceding goal turn produced verified phase-1 code; this continuation adds implementation and executed evidence. The full FYP-I goal remains active. `ACCEPTANCE_MATRIX.md` retains the complete requirement audit.

### Implementation

- Three additive session tables; no identity-column changes. User/organisation-scoped lifecycle, stable pagination, history/resume, outcomes and exact saved turn responses/evidence.
- Owner-only writes; same-organisation supervisor/admin read access; inaccessible IDs return 404. Service/demo principals cannot access user investigations.
- Conditional revision/open-state updates make turn/snapshot persistence atomic across processes. Stale/concurrent/closed turns return 409; failures roll back the revision too. Browser-supplied state cannot replace saved state.
- Model-outage session replies derive from ranking/evidence, with validated citation IDs and honest unavailable status. The stateless Copilot outage contract remains unchanged.
- Quick-diagnose opt-in degraded mode; prompt-bounded citation/rare-case allow-list; content/count/mode/prompt-aware cache identity; malformed/empty-cache tolerance and atomic cache replacement.
- Escaped authenticated HTML reports for closed sessions. One-click frontend integration remains WP-S9.
- CI runtime-error lint through Ruff (a development-only dependency explicitly required by WP-S11); terminal/XML coverage, JUnit artifacts and PostgreSQL session contracts. Docker CI also runs the production-startup session smoke. Removed an unreachable duplicate diagnostics prompt block exposed by lint.
- Form 10 working template distinguishes a documented proposal-defense statement from missing Mid-I feedback. No feedback/signatures invented.

### Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Full local backend, real Neo4j/PostgreSQL plus memory/SQLite | **293 passed**, zero failures/skips | `evidence/phase2-backend-full.txt`, JUnit/XML |
| Session contracts on both SQL backends | 22 initial tests; four further atomic-state tests; final fallback-citation test on both | `phase2-session-tests.txt`, `phase2-atomic-state-tests.txt`, `phase2-final-citation-boundary.txt` |
| Opt-in degradation, malformed caches, bounded citations, content invalidation | **8 passed** | `phase2-degraded-tests.txt` |
| Original diagnostic/adapter/foundation boundaries | **32 passed** | `phase2-existing-boundaries.txt` |
| Runtime-error lint | **PASS** | `phase2-lint.txt` |
| Actual production startup with local Neo4j/PostgreSQL, model off | **SESSION_RUNTIME_SMOKE=PASS** | `phase2-runtime-smoke.txt`, `phase2-runtime-server.txt` |
| Phase-1 GitHub CI/deployment preview checks | All successful | `phase1-github-checks.json`, PR #27 |

The production smoke verified authenticated create/turn, ranking/evidence/template with the model off, exact saved replay in a second HTTP client, another technician's 404, admin read/403 mutation, closure/409 future turns and a citation-bearing HTML report. Its first harness request used the wrong ingest key; corrected the harness to the existing `csv_path` contract and reran successfully. No maintenance API change was made.

Broad coverage includes retained legacy and is below 80%; the new session modules have separately measured coverage in `phase2-coverage-summary.json`. The final fallback-citation lines were added during the full run and were separately verified afterward; remote CI will measure final source. NFR-04 is not claimed complete.

Coverage initially triggered SQLAlchemy's known dotted-source import/reimport issue (`InternalTraversal` mismatch). Normal tests passed; using filesystem/top-level coverage sources avoided the import side effect without changing runtime dependencies. [Upstream issue](https://github.com/sqlalchemy/sqlalchemy/issues/13645). A test-only PostgreSQL URL was also normalized through the existing psycopg2 adapter. Neither workaround skips database contracts.

### Review and remaining work

Phase-1 draft PR: https://github.com/umaritics/halite/pull/27 — backend, frontend, Docker smoke and Vercel checks all succeeded. No main merge or shared-staging write occurred. Phase-2 draft review/CI is next.

Research policy/questions/grounding are explicitly unconfigured: responses abstain provisionally with `policy_status=not_configured` and null beliefs/questions/grounding. This is an intermediate persistence milestone, not the final decision product. The remaining packages, frontend integration, measured experiments, genuine human labels/model decisions, report/defense and release gates stay open in the acceptance matrix.

Knowledge updated: investigation context/flow/decision; diagnostics and CI context/flows; registry/index/router. AI assistance: Codex authored code, tests and engineering evidence; student/supervisor judgements, labels and approvals are not claimed.

### GitHub acceptance and visual proof

Phase-2 draft PR: https://github.com/umaritics/halite/pull/28 (stacked on #27). GitHub run https://github.com/umaritics/halite/actions/runs/44702502396 verified commit `4764581`: **293 tests, zero failures/errors/skips**, clean lint, uploaded JUnit/coverage reports, frontend tests/build and both Docker runtime smoke checks. Vercel preview also succeeded. Downloaded artifact source and metadata are preserved in `phase2-github-*`; broad measured coverage is **75.47%**, not an 80% claim.

The printable report was opened in headless Chrome using print CSS at 1280px, visually inspected for clean headings/text/evidence, and tested with a maximum-length unbroken title at 1280px and 794px. Added `overflow-wrap:anywhere` to keep that valid input within page bounds. Both widths report no horizontal overflow; evidence: `phase2-report-print.png`, `phase2-report-render.json`, `phase2-print-report-tests.txt` (both database backends). This final small print-layout follow-up is locally verified and will receive a fresh GitHub check after push.

The temporary HTTP server has been stopped. The two disposable databases remain on separate loopback ports for continued goal verification; their storage is tmpfs. They are not shared staging and will be removed when no longer needed.

## Phase 3 — investigation frontend feature package

Branch `codex/usman-investigation-ui`, stacked on phase 2. Added server-backed history/workspace, explicit provisional decisions, offered question controls, saved evidence replay, outcome dialog, authenticated report printing, degraded quick diagnosis and partial-failure home widgets. Account-keyed components reject late previous-account responses. Uncertain writes require a server reload before further mutation; the draft clears only when saved state proves the observation committed. Legacy unowned browser keys are discarded, never imported.

Verification: **246 frontend tests passed in 24 files**, main build and independent feature-preview build passed; targeted backend boundaries **12 passed**. A real browser against disposable PostgreSQL/Neo4j exercised login, create, model-off turn, evidence, closure, print, second-browser resume/reload without inference, outsider denial, quick diagnosis and hidden failed summary widget. Dark/light screenshots at 1280px have no horizontal overflow or page errors. Evidence is in `evidence/phase3-*`; `phase3-browser-proof.json` explicitly identifies the independent preview harness. Fixed an inaccessible symptom label found during browser checking. Light-mode screenshot waits for the existing colour transition to finish.

The actual shared App/Sidebar/AuthContext were intentionally unchanged in this package. The user subsequently authorized **“Prepare the integration for review”**; the concrete patch is recorded in `FRONTEND_INTEGRATION.patch` and will be applied/tested on a separate branch. This is not Shahmeer review, merge or deployment approval. The React quality review checked effect cleanup/account isolation, async mutation guards, labels/dialogs, parallel independent dashboard reads and absence of session local-storage persistence. No new dependencies. Research calibration/grounding/evaluation and human decisions remain open.

Phase-2 follow-up commit `ffafbaf` also passed all GitHub checks; evidence `phase2-final-github-checks.json`.
