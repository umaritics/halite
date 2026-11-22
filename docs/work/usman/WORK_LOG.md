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

## Phase 3 integration — user-authorized shared-file preparation

The user answered **“Prepare the integration for review.”** Created separate
`codex/usman-ui-integration` from feature commit `51b87a3` (draft PR #29). Applied
minimal shared manifest registry, authenticated App routes, Sidebar nav, home
defaults and AuthContext legacy-key clearing. Kept Shahmeer's broader preparation
outside the change; owner review remains pending. Added route/privacy tests and
updated the invite test's destination fixture without weakening authentication.

**256 tests passed in 25 files; main production build passed.** BrowserRouter
verification through the actual App shell and local API/Neo4j/PostgreSQL passed:
create/model-off turn/saved evidence, close/print, second-browser/reload without
inference, outsider denial, quick diagnosis, failed-widget hiding, dark/light,
old Diagnostics redirect, logout key clearing, protected URL after logout and
next-account isolation. Screenshots visually inspected at 1280px; no overflow or
page errors. Evidence `phase3-integration-*`. Build retains the existing large
graph-heavy application chunk warning; no suppressed warnings or false claim of
research policy readiness. This phase is review-ready, not merged/deployed.

The browser flow was rerun against the built production bundle served locally
by Vite preview on port 15174, including direct-route refresh and JWT API proxy;
**INVESTIGATION_UI_PRODUCTION_SHELL=PASS**. PR #29 feature CI also passed all
backend/frontend/Docker/Vercel checks (`phase3-feature-github-checks.json`).
Temporary HTTP servers were stopped after verification; disposable database
containers remain isolated for subsequent work.

Integration implementation commit `8ae9b8d` is published in draft PR #30:
https://github.com/umaritics/halite/pull/30, base feature PR #29. The draft remains
unmerged for Shahmeer review. This reference records preparation, not approval.

### Hosted integration acceptance

PR #30 commit `fedbdc5` passed every hosted check: backend tests, frontend
tests/build, Docker real-graph/session runtime smoke, Vercel preview and preview
comments. Run: https://github.com/umaritics/halite/actions/runs/44707539568.
Machine-readable check links/states are saved in
`evidence/phase3-integration-github-checks.json`. Code remains unmerged; owner
review is the outstanding integration gate. Final evidence follow-up changes
documentation only.

## Phase 4 — decision core, stored beliefs and measured selection

Branch `codex/usman-decision-layer`, stacked on PR #30. The preceding goal turn
made concrete progress by publishing/review-verifying the shared integration.
PR #30's final documentation commit subsequently passed every hosted check too.

### User authorization and design before code

When asked for the plan's reserved design note, the user answered: **“just do it
on my behalf you know the project wayy better than me so go ahead do something
that is impressive.”** This authorizes the AI-assisted design draft at
`docs/fyp1-final/DECISION_LAYER_DESIGN.md`, written before the WP-S4 implementation.
It explicitly discloses assistance. It is not an invented unaided student note,
human label, cross-review or supervisor approval. No numeric operating-point
choice is claimed from that response.

### Implementation and executed evidence

- Pure stable top-ten/other softmax, entropy, explicit uncalibrated fallback and
  version/provenance-validated fitted parameters in `beliefs.py`.
- Pure answer/ask/abstain priority, exact boundaries, question budget, active
  evidence gate, report-mode option and recorded rule inputs in `policy.py`.
  Missing configuration still abstains; no production threshold was guessed.
- `ranker_port.py` centralises investigation ranking imports and provides the
  future V1 extension boundary, honest missing-extension fallback, and an error
  rather than ignoring an unsupported historical time bound. Frozen diagnostic
  endpoints keep their exact Mid-I score/context behavior.
- Additive uncalibrated beliefs/policy inputs in stateless Copilot; sessions store
  exact beliefs/entropy on snapshots and preserve old saved replies.
- Relative-support UI now includes the other bucket and entropy, even with no
  named candidates. Fitted support also retains the relative-support label.
- Streaming official FAA source projection, timestamp/chain-safe offline adapter,
  deterministic NLL fitter, 2024 threshold table and 1,000 clustered bootstrap
  intervals. No new application dependency, model calls or other-owner code.

**321 backend tests passed**, zero failures/skips, using real Neo4j/PostgreSQL
where required and memory/SQLite contracts. **258 frontend tests passed**; main
build passed; runtime-error lint passed. Production-startup smoke with disposable
Neo4j/PostgreSQL verified normalized uncalibrated beliefs, unconfigured abstention
and exact cross-client snapshot replay. The actual built application passed its
browser flow including relative-support bars, second-browser/reload without
inference, outcomes/print, outsider denial, widget failure, model-off diagnosis,
redirects/logout/account isolation. Dark/light 1280px screenshots visually checked;
no horizontal overflow or page errors. Evidence: `evidence/phase4-*`.

The initial API test command named a nonexistent test file, so it collected no
tests; corrected to `test_investigation_degraded.py` and reran (62 passed), then
ran the complete suite. No failing assertion was removed.

### Real-data selection and protocol audit

The FAA endpoint was verified accessible and streamed 62,691 records for 2023 and
66,080 for 2024. Compressed projections are git-ignored and checked by canonical
row fingerprint; source metadata is committed. The shared contract's **2023 fit /
2024 select / 2025 test** wins over the guide's conflicting 2024 fit wording.
`2025` was neither downloaded nor evaluated in this phase.

The first exploratory run retained only the earliest correction per original.
A protocol audit found 35 additional eligible fit pairs and 49 selection pairs.
Corrected the method to retain every eligible pair, and clustered bootstrap by
original report to retain their dependence. Preserved the correction reason in
`phase4-protocol-correction.json`; it is a selection-method change before any
held-out evaluation.

Authoritative results: `backend/investigation/experiments/results/decision_selection_2024_v2/`.
**406** fit pairs, **389** selection pairs from **340** originals; 22/7 unknown
outcome keys excluded and counted. T=0.5025466938, other score=1.3184610197;
mean fit NLL=1.1940390452; fitted optimum is inside the recorded search domain.
The no-abstention baseline answers 388/389 with top-1 0.1443, top-3 0.2062 and
unsupported top-3 outcome-key rate 0.7918 over all selection cases. At threshold
0.20 with at least two active records: 43/389 answered, top-1 0.4651, top-3 0.5814,
unsupported rate 0.0463. These are **selection examples, not a chosen point or
held-out result**. Their 95% clustered intervals are in the JSON. Named-top ECE
on selection is 0.06891; this does not authorize probability wording.

These weak historical part-key results remain visible. They are a proxy from the
bounded Mid-I ranker, not validated fault diagnosis. Scores/case IDs are committed
for reproducibility, with source/method fingerprints and truthful dirty-tree
provenance. Offline occurrence-date ties use record ID descending; live Cypher
has no secondary key, explicitly disclosed. No graph or retrieval-owner algorithm
was changed.

### Remaining acceptance

This phase completes the core and pre-question selection slice, **not all WP-S4
or FYP-I**. The question-conditioned selection and operating-point decision,
held-out 2025 run/intervals, plots/product experiment panels, calibrated runtime
activation, sentence checker/labels, model comparison and release gates remain.
Broad test coverage is approximately 76%, still below NFR-04; no threshold or
coverage exclusions were changed to hide it. See the complete acceptance matrix.
Knowledge context, flow, decision/index/registry and the guide's implementation
snapshot were updated in the same change set.

The committed experiment method fingerprint was recomputed against the final
source and matched exactly (`EXPERIMENT_METHOD_FINGERPRINT=PASS`). The temporary
API/preview servers were stopped after browser verification to freeze their logs.
Disposable database containers remain isolated for subsequent phases.

### Published review and independent score replay

Draft PR #31: https://github.com/umaritics/halite/pull/31, stacked on #30.
`verify_decision_selection.py` verified the final method fingerprint and reproduced
the fit, every selection/stratified metric and all 1,000-draw intervals exactly
from committed score cases, with no graph/network/model access. Evidence:
`phase4-selection-replay.txt`. It also found 246/389 outcome keys absent from the
retrieved top ten and 309/389 absent from the top three. The generated error
analysis retains these negatives and gives deterministic examples without
inventing human adjudication. This identifies why reweighting a fixed candidate
list cannot by itself repair many misses.

Case-score JSON formatting was compacted with parsed-value equality checks to
keep the review small; no values or calculation sources changed. Removed a
trailing blank line in a captured test log after the whitespace check flagged it.

### Hosted acceptance

PR #31 implementation and replay/error-analysis follow-up (`cb8200b`) passed
all hosted checks: backend tests, frontend tests/build, Docker real-graph and
session runtime smoke, Vercel preview and preview comments. Run:
https://github.com/umaritics/halite/actions/runs/44715865191. Machine-readable
check links/states are preserved in `evidence/phase4-github-checks.json`. This
evidence-only commit does not change behavior or experiment calculations.

## Phase 5 — offline question core and measured selection

Implemented thirteen frozen report attributes, official FAA code descriptions,
validated expected information gain/Bayesian updates, smoothed likelihoods and an
incremental strict-submission-time index with full query-chain exclusion. The
codebook is exactly reproducible from the retained official archive. Source:
https://sdrs.faa.gov/Documents/SDRS%20Look-Up%20Tables.zip (archive SHA-256
`5ab1d86f963a2f7c2ac2298c787bc875d5212aa4cd6f82df076122958651ced0`).

Ran the original-report simulated technician on all 389 frozen 2024 pairs / 340
originals. Compared information gain, seeded random and no questions using all
thirteen, six structured and four coded attributes. Every likelihood uses earlier
submissions outside the entire query chain. Correction parts are evaluation-only.
Narrative mentions explicitly include negative mentions and can reuse initial
text; structured-only controls expose that distinction. No 2025 source was read.

At three questions, all-attribute top-1 is 0.2082 versus random 0.1799; paired
95% interval for the difference includes zero. Top-3 differences also remain
uncertain. Entropy reduction is clearer, but is not proof of diagnostic accuracy.
Results, individual traces and 1,000-draw clustered intervals are committed under
`backend/investigation/experiments/results/question_selection_2024_v2/`.
No operating point, real-human answer or production question handling is claimed.

Verification: **342 backend tests passed** with real isolated Neo4j/PostgreSQL,
including hand-computed gain, not-sure, future/equal-time and chain exclusion,
indexed/naive counting equality and complete synthetic experiment output. Ruff
passed. `verify_question_selection.py` exactly reproduced all saved metrics and
intervals, code-source hashes and official archive extraction without network.
The pre-question baseline replay still matches all values and its original method
fingerprint; its manifest now enumerates its frozen dependencies so new unrelated
experiment files do not invalidate it. Broad backend coverage remains 76%.

Generated a standalone PNG/PDF scientific figure with Matplotlib 3.9.4 in a
separate reporting environment; no app dependency added. Visually inspected the
nine-panel figure: readable legends, confidence bands, caveats and axes, no clipped
text. Updated context, flow, registry/index, decision and acceptance matrix.

The user authorized applying/testing the twelve-line coded-field patch on a
separate review branch before backend preparation merges. That next change must
retain pending Shahmeer review and Umar's actual staging backup/backfill. Live
question integration and all remaining acceptance matrix items stay open.

### Published question core and authorized coded-field review preparation

Question package draft PR #32:
https://github.com/umaritics/halite/pull/32 (stacked on #31). All hosted checks on
`bb5502f` passed: backend, frontend/build, real-graph Docker smoke, Vercel preview
and comments. Exact check states/links: `phase5-question-github-checks.json`.
The generated table had a trailing blank line; removed in `bb5502f` without
changing calculation sources or parsed result values. Fetched origin again;
main remains `0dd86d9` (master-plan merge), so no new main code was overlooked.

On `codex/usman-coded-fields-integration`, applied exactly the approved twelve-line
patch to three shared files. Added the dry-run-default exact-ID backfill tool and
13 additional checks (355 backend tests total). Both memory and actual isolated
Neo4j round-trip CSV codes as strings and retain duplicate ingest behavior.
Backfill validates every source row before connecting, rejects conflicting source
duplicates, preserves existing-value conflicts and blank sources, reports missing
IDs and includes source SHA/prior field values in its reviewable JSON. It touches
no graph identity/link, ranking, confidence or text fields. Missing optional codes
remain blank. Writes fail explicitly and are resumable/idempotent, not falsely
represented as a multi-record transaction.

Actual CLI proof: `verify_coded_fields_cli.py` creates one uniquely identified
synthetic old Neo4j node with no coded properties, invokes the real command for
--dry-run / --apply / --apply, verifies leading zero strings, unrelated property
preservation and second-apply zero changes, then cleans up only that node. Saved
JSON: `phase5-coded-fields-cli.json`. No shared staging accessed. Full 355-test
JUnit/log and Ruff output are committed. The sole warning is the existing AnyIO
BlockingPortal deprecation. Broad coverage is still 76%, not the 80% target.

User authorization is explicitly recorded in the handoff and decision. Shahmeer
owner review, merges, and Umar's staging backup/backfill remain pending; this
phase completes review preparation/testing, not deployment or all of WP-S5.

Official code coverage is additionally preserved in `phase5-faa-code-coverage.json`:
all 128,771 loaded 2023/2024 records have zero unknown nonblank codes across the
four official tables. The graph ingester still preserves arbitrary raw codes
without pretending to validate their meanings. Relabeled the figure's horizontal
axis “Question budget (maximum)” to accurately include empty/no-question cases.
No metric, trace or method source changed.

Coded-field review preparation is draft PR #33:
https://github.com/umaritics/halite/pull/33, stacked on #32.

## Phase 6 — durable live question and posterior flow

Implemented the managed session controller behind disabled-by-default
`SESSION_QUESTIONS_ENABLED` and an explicit `SESSION_POLICY_FILE`. The committed
fixture is synthetic and experimental, not Usman's selected operating point.
The default session/stateless contracts remain unconfigured; no production
threshold, 2025 result or probability wording is installed.

One read-only graph snapshot now supplies both ranking and likelihood counts.
It excludes missing/invalid/naive/equal/future submission times before retrieval
limits, uses real ABOUT membership, and prevents known future corrections from
changing earlier visible supersession status. Likelihood counts exclude validated
query citation chains and save audit/count metadata. The existing ranker algorithm
and other owners' data/retrieval files are unchanged.

Each question saves a unique ID, fixed hypothesis basis, likelihood matrices,
codebook and policy. Answers must match ID/attribute/options, then update **saved**
beliefs without graph/model reads. Saved configuration survives file changes and
application restart. The turn stores prior, posterior and answer; not-sure changes
no beliefs but excludes the attribute. Budget/history survive later observations.
The existing CAS transaction rejects concurrent/stale answers and closure races;
snapshot failures roll back question consumption and revision together.

Managed prose follows the server decision. The model cannot set question/decision
fields. Empty/model-written question prose falls back explicitly. Structured
answers use `llm_status=not_needed`; their citations validate against saved evidence.
Stateless Copilot uses its same helper with default behavior; compatibility tests
pass unchanged. No shared shell source was edited in this package.

Frontend now submits the saved question ID, resets choice on question identity
change, disables pending answers, and labels experimental guidance while keeping
relative support/other/entropy. **261 frontend tests passed**, and production build
succeeded. The React quality review checked hook order, keyed reset, controlled
options, accessible labels/disabled state, confirmed-response updates and no new
client-side persistence/dependencies.

Built-browser proof through actual App/Sidebar/AuthProvider/API with real local
Neo4j and isolated PostgreSQL: 40 synthetic coded records; real user login/session;
answer changes bars; two not-sure answers preserve beliefs; budget three ends in
abstention; reloads create no extra turn and reproduce exact saved responses.
`/api/health` agrees: graph_mode=neo4j, auth_db_mode=postgresql, llm_mode=fallback,
maintenance_corpus_loaded=true after ingest. No live LLM or shared staging claimed.
Evidence: `phase6-browser-proof.json`, screenshots, server logs and browser output.

Setup correction: an initial `/tmp` ingest source was correctly rejected by the
existing file-path guard. Moved the synthetic fixture into the allowed test-fixture
directory, then the complete flow passed. The first rollback test also incorrectly
queried while its deliberately broken snapshot constructor was still patched;
restored that constructor before reading the verified database state.

Visual QA caught a separate shared-shell phone issue: a fixed 256px sidebar leaves
too little content width. The initial no-overflow assertion was insufficient; the
phone screenshot is explicitly failure evidence, not a usability pass. Prepared
an unapplied App/Sidebar responsive patch and requested its narrow ownership
handoff. The user authorized “Prepare and test the separate layout branch”. It
will be applied/tested separately with Shahmeer owner review/merge pending.

Focused live-question checks cover both SQLite/PostgreSQL, healthy/rejected model
prose, answer/report priorities, source/parameter mismatches, restart, question
replacement, stale/unoffered/foreign answers, concurrency, closure and rollback.
The saved 2024 experiment still exactly replays all three controls and intervals;
its source/method files were not changed. See phase6 replay evidence.

Final phase-6 backend run: **384 passed** against isolated Neo4j/PostgreSQL,
with JUnit and broad coverage output saved. Coverage is 77%, still below NFR-04's
80% target; no exclusions or target reductions were used. Ruff passed. The full
suite includes all pre-existing tests plus the new managed-question paths.

### Phase 6 hosted acceptance

Draft PR #34: https://github.com/umaritics/halite/pull/34, stacked on #33.
All hosted checks on `a73cce9` passed: backend tests, frontend tests/build, Docker
real-graph/session smoke, Vercel preview and preview comments. Machine-readable
states/links are saved in `phase6-github-checks.json`. No shared source was bundled
into this question package. The proposal patch has required unified-diff context
spaces; whitespace checks exclude that patch text and check all actual code/docs.

## Phase 7 — authorized responsive-shell preparation

Applied exactly the prepared App/Sidebar patch on
`codex/usman-mobile-integration`; reverse-application validation passes. The user
explicitly authorized this separate preparation after seeing the ownership reason.
No broader frontend preparation, design system, API client or auth logic changed.
Shahmeer owner review and merge remain pending.

Below md: fixed 64px icon rail, accessible destination/sign-out names and scrolling
navigation. At md and above: existing 256px sidebar retained. Main's flex item
uses min-width:0. Roles, review badge and confirmed logout behavior stay intact.

**264 frontend tests passed**, including accessible active destinations/roles and
logout wait/redirect. Production build passed. React review checked conditional
classes, accessible icon names, unchanged hooks/roles and source scope. Existing
large-bundle warning is unchanged; no app dependency was added.

The production-built real browser verified the complete question flow again with
strict mobile assertions: at 390px, main is **326px** and the active select is
**260px**, contained from x=97 to x=357. It submitted the actual answer at phone
width, then verified moving bars, two not-sure updates, question budget three,
exact saved response/reload without extra inference and the 256px desktop sidebar.
Phone keyboard navigation to history and back created no inference turn. Icon-only
sign-out returned to login; a protected investigation deep link stayed behind
login without revealing its title. No browser exceptions or horizontal overflow.
Proof: `phase7-browser-proof.json`, `phase7-browser-run.txt` and screenshots.

Visually inspected desktop and active-phone screenshots: the question/options,
submit action and supporting context are readable; the old narrow-column failure
is resolved in this review branch. Retained the initial phase-6 failure evidence
rather than relabelling it as success. Updated context, flow, registry, decision,
acceptance matrix and the handoff procedure together. Stopped local API/preview
servers after verification; disposable databases remain for subsequent phases.

Published responsive review preparation as draft PR #35:
https://github.com/umaritics/halite/pull/35, stacked on #34. Final local shutdown
lines from the API were captured after the implementation commit; this follow-up
only preserves that evidence and the PR link. Hosted acceptance is available in
https://github.com/umaritics/halite/pull/35/checks. The working tree must remain
clean and no owner review/merge is implied by local or hosted verification.

## Phase 8 — sentence audits and independent review preparation

Fetched origin again; main remains `0dd86d9` and preceding review branches remain
unmerged. Continued on separate `codex/usman-grounding`, based on PR #35. No
merge, staging deployment or teammate message was performed.

Implemented the L2/L3 checker, optional encoder port, 2023-only fitted part guard
vocabulary (1,006 names), versioned configuration loader and additive session/
quick-diagnosis integration. Each audit retains original sentence text, cited IDs,
source narratives, max single-report score, lexical guards, mode and provenance.
Thresholds/whitelist default to absent: valid citations stay **unrated**. Invalid
citations fail L2. Dense outages retain lexical scores but withhold blended-mode
ratings. Structured answer audits make no graph/encoder call. Settings are frozen
before inference; invalid next-turn settings fail before inference. Saved response
and grounding JSON commit/replay together through the existing transaction.

The UI preserves sentence Markdown, labels pending/experimental status and exposes
focusable reasons/source narratives. Quick diagnosis keeps its original response
fields and adds full source text inside the grounding audit. Frozen stateless
Copilot prose/output behavior remains unchanged.

Prepared a reproducible, blinded 150-pair constructed sample from actual FAA
2023/2024 text: 50 originals, three pairing categories, 99 fit / 51 validation pairs,
no source-ID overlap across splits and no held-out 2025. **Muhammad Umar** is the
second independent reviewer chosen by the user. Separate Usman/Umar HTML copies,
empty CSV templates, draft resume/export, fingerprint-bound strict import,
agreement/adjudication and lexical threshold proposal tools are provided. No
labels, rationales, signatures, threshold acceptance or human agreement results
were invented. These are constructed calibration pairs, **not measured generated
model answers**. L4/generated-answer/no-evidence results remain separate work.

Verification found and corrected a real-corpus ID-shape issue: the legacy
letters-then-digits assumption missed mixed-prefix and numeric-leading FAA IDs.
The new grounder supports those shapes independently; frozen legacy citation
behavior remains intact. Added four parametrized regression cases and audited
**all 150 actual packet claims** for one sentence and exact source-ID recognition.
The corrected final packet's method hashes and blank templates are verified by
`verify_grounding_packet.py`.

**420 backend tests passed** on SQLite and isolated real PostgreSQL/Neo4j, with
JUnit and the same broad coverage scope as CI; coverage is **78%**, still below
NFR-04's 80% target. **267 frontend tests passed**, production build and full
backend Ruff passed. The first backend invocation used an unavailable driver
name (`psycopg` instead of the installed `psycopg2`); its setup-error log is retained,
and the corrected full run passed. No new application dependency was installed.

Real Chromium checked the actual 150-pair interface with **zero human labels
entered**. A separate six-pair synthetic packet tested partial-export rejection,
draft roundtrip with unsaved fields, mixed-reviewer rejection, foreign-fingerprint
rejection and complete CSV export; its CSV also passes the strict importer.
The synthetic reviews are not copied into the human packet. Visually inspected
the empty reviewer page and built application sentence marks.

The production-built BrowserRouter flow uses real local databases and accurately
reports `llm_mode=fallback`. It verified sentence audits in both initial and
structured-answer turns, pending-rating labels, changed bars, not-sure handling,
three-question budget, phone controls, keyboard/logout and exact GET/reload replay
without extra inference. A first verifier selector matched two historical sentence
summaries; narrowing to the first summary resolved that test ambiguity. Both logs
are retained. Full project acceptance is still tracked separately in the matrix.

Visual QA also found that deterministic model-off diagnosis cites the complete
collected evidence list, whereas model-written diagnosis sees a bounded prompt.
Corrected the fallback audit to use its actual supplied/displayed sources, keeping
the stricter prompt list for model prose. Added a regression demonstrating the
same eighth source is valid in the deterministic summary and invalid outside the
model prompt. **Nine final runtime tests passed**, including PostgreSQL, after
this correction; the prior 420-test broad suite remains recorded separately.
A built-browser quick-diagnosis check opens a citation by keyboard focus and
matches the exact saved narrative. No frozen explanation text was changed.

Published draft PR #36: https://github.com/umaritics/halite/pull/36, stacked on #35.
Local API/preview servers were stopped after verification. Proof text logs have
only trailing whitespace normalized; original outcomes/errors are retained.
Hosted verification is tracked on the PR checks page and must be green before
this preparation is treated as CI-verified. Owner merge/release remains pending.

## Phase 9 — portable interactive-model comparison

Previous goal turn classified **progress**: committed saved grounding audits and
review tools, with PR #36's final `572fcc6` passing all hosted checks (421 backend
tests, frontend/build, Compose and preview). This turn continues the whole goal;
it does not treat that package as completion of the FYP.

Started `codex/usman-model-evaluation` from #36. Fetched origin; main still ends at
`0dd86d9`. After asking about M4 availability, the user explicitly chose **“finish
and verify a self-contained runner that he can execute on the M4.”** No endpoint
or real M4 output was supplied, and no teammate message was sent.

Implemented:

- `model_prompts.py`: reproducible 20-unique-original packet from the exact frozen
  real 2023/2024 selection corpus. Ten extraction and ten prose prompts, plus ten
  paired no-evidence prose calls per model. Top-three hypotheses / at most three
  source IDs each. Strict earlier submission and full-chain exclusion verified;
  no correcting narrative, answer key or answer ID is exported. 2025 untouched.
- `model_compare.py`: native Ollama HTTP, exact names/digests/server version,
  runner hardware and explicit measurement roles, serial timing, excluded warmups,
  seeded order, fixed context/token limits, strict output/citation checks, saved
  sentence audits, raw response/error journals and generated decision table.
  No retries, fallback, model pull, automatic winner or app configuration changes.
  Invalid/unavailable support calibration stays unavailable. A loopback tunnel is
  explicitly not proof of inference-server placement.
- Durable resume preserves attempts and verifies packet/method/model/machine and
  saved assessment identities. Resumed unfinished models are rewarmed; finished
  runs make no more chat calls. Partial journal tails fail without dropping bytes.
- `model_bundle.py`: deterministic ZIP with fixed member order/timestamps/modes,
  source/data hashes, fixed bundled packet and entrypoint integrity verification.
  The extracted package needs Python standard library only, plus an already
  installed/running Ollama service and models. No database/app/server install.

The delivered artifact is `artifacts/halite-model-comparison-v1.zip`, with SHA-256
sidecar and `MODEL_COMPARISON_RUNNER.md`. Rebuilding independently produced exactly
identical ZIP bytes. No real-model results, human labels or M4 timing are bundled.

**Eleven standard-library unit tests passed.** They check exact denominators, raw
response retention, completed/partial resume, failed attempts, changed model
identity, tampered journal/packet/bundle, strict fact/prose validity, missing
calibration, fake M4 roles, endpoint constraints, verified 7–8B candidate metadata and prompt context budget.
They remain discoverable by the repository's pytest suite through unittest.

A real local HTTP server with explicitly **synthetic** responses exercised the
extracted runner under `python -I -S`: no site packages, 31 chat posts (one excluded
warmup plus 30 cases/arms), exact journal replay with no extra calls on resume.
A separate injected HTTP outage produced a retained failed attempt, 29 responses
from 30 attempts and CLI exit 2 after saving the table/results. All actual packet
sources were independently checked against the frozen corpus for chronology,
chain exclusion, verbatim text and generator hash. See `phase9-*-proof.json` and
unit/build logs. These are transport/tool verification, not research model scores.

The environment's temporary state had been reset: prior venv and test database
containers were absent. A full dependency restore failed for disk space. Kept
that failure log; replaced the unnecessary local dependency requirement with
standard-library tests and isolated-Python HTTP verification. A subsequent minimal
installer was stopped once these checks no longer needed it. No user data or
other project's containers were removed. Full regression/lint/coverage acceptance
will be checked through the existing hosted CI, which provisions its own databases.

Updated the knowledge router/index/registry, model context/flow, decision, guide
and acceptance matrix in the same change. Actual M4 execution, comparison review
and Usman's interactive-model decision remain gates for the full FYP objective.

Published this package as draft PR #37:
https://github.com/umaritics/halite/pull/37, stacked on #36. The final eleven focused
tests and extracted HTTP smoke passed. Hosted full regression/lint/coverage,
Compose and preview checks are tracked on that PR. The artifact's exact source
and instruction bytes are frozen by its manifest and sidecar; this handoff log
does not change the ZIP. No approval, merge, M4 result or model decision is implied.

## Local machine incident and authorized storage cleanup

User reported two hard freezes. Stopped project execution for lightweight checks;
confirmed full-disk write failures in an earlier boot, but no proven freeze trigger.
After explicit user authorization, cleared npm content cache, then emptied Trash
and removed four known downloaded app packages/archives. The latter operation
freed about 18.2 GiB; root now has about 21 GiB available (77% used). No project,
application, container volume or browser data was removed. Remaining large items
require the user’s decision. Evidence and resource constraints are recorded in
`LOCAL_MACHINE_INCIDENT.md` and `evidence/local-storage-cleanup-20261120.json`.
Full local installs/builds/parallel workloads must not resume under low storage;
use hosted CI and lightweight serial checks. Freeing space is not proof that the
underlying freeze cause has been fixed.

### Machine stability follow-up

Cleared Docker build cache (3.309 GB reported reclaimed) and verified zero remaining build cache, root 24 GiB free / 74% used. Preserved containers/images/volumes. Three unrelated cluster containers consume about 3.7 GiB in one sample; retained pending user decision. Last goal activity was research API implementation/dependency restoration; no logged evidence establishes the freeze trigger. Full verification will use hosted CI, with serial lightweight local checks and a 10 GiB free-space guard. See `LOCAL_MACHINE_INCIDENT.md` and `evidence/docker-cache-cleanup-20261120.json`.

### Phase 10 — research publication API

Refreshed origin; main and existing review branches remain unchanged. Implemented
website-user-only GET /api/sessions/experiments with exact checksum-pinned 2024
artifacts. Corruption/missing evidence returns 503; explicit empty state supported.
No model, graph, fitting, accepted point or held-out result invented. Twelve pure
publication tests passed in 0.100 seconds using standard-library Python only.
Real JWT/route-order/error tests added for hosted CI; not yet executed locally.
An initial test-file write used an incorrect relative directory and created no
files; corrected the paths and ran all twelve actual tests. No dependency install
or container/model workload started locally. Product charts remain in progress.

### Shared chart review preparation

Isolated the plan-required Recharts/shared wrapper on codex/usman-chart-foundation-review. Shared components are proposed for Shahmeer review; existing pages and shell are not refactored. Metadata preparation only, with a 384 MiB Node heap cap and scripts disabled; no package installation or full local build. Official ErrorBar documentation confirms asymmetric distances. Hosted verification pending.

### Phase 10 — product research panel preparation

PR #38 hosted checks all passed (workflow 44745242226): backend/JWT route tests,
frontend tests/build and Docker real-graph smoke. Shared-chart PR #39 exposed a
missing matchMedia implementation in jsdom; corrected its test browser API setup
in commit 2f4c50b, with no production workaround. Prepared Usman's product page,
real-artifact component contracts and a hosted production-browser verifier.
Includes all policy/attribute controls, cohort selection, top-1/top-3/entropy in
bits, paired intervals, accuracy–coverage and clearly labelled outcome proxy.
No point accepted; no 2025 or sentence hallucination measurement fabricated.
Hosted browser checks use real endpoint reads and explicitly mock only UI
outage/empty subchecks. Screenshots/proof will be retained from CI.

Hosted run 44746788033 passed backend/frontend checks but exposed a runner setup issue: Compose had created a root-owned frontend/node_modules mountpoint, so host npm ci failed EACCES before browser execution. Corrected the browser preparation to build a git-archived frontend copy under RUNNER_TEMP; no broad permission change or local workaround. Browser verification is still required.

Hosted run 44747282289 on 7aeddb2 passed all jobs: 445 backend tests, 275 frontend tests, both builds, real-graph/session smoke and production-browser proof. Downloaded and inspected desktop/light, dark accuracy–coverage and phone screenshots. Browser verified real JWT publication hashes, three SVG charts/whiskers, saved table values, controls, deep-link reload, both themes and phone geometry, and explicitly mocked outage/empty/retry states. Visual inspection found fractional question-budget tick labels; changed the shared wrapper to accept saved ticks, supplied exact recorded budgets from the feature, and extended browser assertions. This additive shared-wrapper change remains subject to Shahmeer review along with the foundation proposal.

Run 44856533622 passed backend/frontend but the added integer-axis browser assertion returned no labels. Inspected the published Recharts 3.11.0 CartesianAxis source (tarball only, no install): tick labels render via a separate SVG layer under recharts-xAxis-tick-labels, not inside recharts-xAxis. Corrected that test selector and explicitly wait for the first label; retain equality against all four saved budgets.

### Phase 10 verified handoff

Source ecdc264 / hosted workflow 44856875802 passed all jobs: 445 backend tests, 275 frontend tests, lint, both builds, Neo4j/PostgreSQL/session smoke and production Chromium research checks. Exact 0/1/2/3 axis labels now match committed budgets. Downloaded and visually inspected final chart/phone screenshots; all screenshots, JSON browser proof, job metadata/checksums and filtered test summary retained under evidence/phase10-research-panel. RESEARCH_PANEL_VERIFICATION.md records implementation, acceptance evidence, source versions, owner review and AI-assistance note. Updated matrix and knowledge routing. Source-word highlighting is the next implementation gap; no full-goal completion claimed. Heavy verification stayed hosted; local disk remained 24 GiB free.

### Phase 11 — saved source-word highlighting

Prepared on codex/usman-source-highlighting, stacked after the verified research
panel. New candidate audits save exact UTF-16 source token spans; citation IDs
are excluded, repeated words/negation/quantities retained, and scoring/ratings
unchanged. Four standard-library tests passed in 0.003 seconds, including Unicode
offsets and metadata-only matches. Quick/session pages render validated escaped
marks on sentence hover and citation/badge focus, with original source preserved.
Old audits are never recomputed; stale/invalid positions do not produce marks.
Added focused UI contracts and extended hosted production-browser verification
with a three-record explicitly synthetic Unicode fixture, real quick/session
requests, exact text/mark parity, saved replay and dark/light phone screenshots.
Hosted regression/browser checks are pending; no local dependency install or
heavy workload was started.

Source-highlighting run 44857961828 passed backend/frontend but the browser fixture ingest rejected its stale login JWT after page reloads rotated the session. Preserved the correct product auth behavior; the verifier now uses the latest bearer token observed on the browser’s actual authenticated requests, including after each navigation. Tokens remain only in process memory and are not logged or saved. No auth workaround or credential persistence was added.

### Phase 11 verified handoff

Source 4136fc3 / hosted run 44858279238 passed all jobs: 449 backend tests, 279 frontend tests, lint, builds, real-graph/session smoke and production-browser source checks. Exact Unicode source text, word marks and saved grounding JSON replay verified in both themes and at phone width. Inspected screenshots and retained six source screenshots, combined browser JSON, filtered CI counts and job/file provenance in evidence/phase11-source-highlighting. SOURCE_HIGHLIGHTING_VERIFICATION.md records files, executed checks, AI assistance and remaining gates. Broad coverage remains 78%; full objective remains active. Phase 10 final documentation head 9476086 also passed all hosted checks in run 44857290515.

### Phase 12 — dependency cleanup preparation

Audited 165 backend Python files: no imports of LangChain roots, docx or dotenv;
pandas is actually used by the CSV importer and FAA tools, while pypdf/docx2txt
still serve legacy documents. Removed five unused/redundant direct requirements
and retained the already-installed NumPy 1.26.4 to avoid an unrelated CSV stack
upgrade. Baseline requirements SHA/source and actual prior hosted package versions
retained under evidence/phase12-dependencies. Standard-library import verifier
passed locally; no dependency installation performed. Added hosted pip/installed
reports and real env-file parsing test; full CI verification pending.

Prepared an exact clean-applying shared retirement patch and contract proposal.
The user explicitly authorized “Prepare and test retirement for review” after
seeing the domain/default/API changes and Shahmeer-owned dependencies. Apply only
on a separate retirement review branch; actual owner review/merge/deploy remain
pending. Dependency-only runtime leaves those contracts unchanged.

Phase12 first hosted run 44881679485: dependency resolution/import-root audit
passed, but pytest collection correctly failed because retained scripts import
requests, previously supplied by LangChain. Added its actual baseline version
as a direct dependency and expanded the audit. No successful test claim is made
for that initial run. Reverification required on the corrected commit.

## Phase 13 — authorized software retirement preparation

Applied the exact approved importer/domain patch on a separate review branch.
Removed all plan-named software runtime files/root scripts and regression suite;
unregistered routes and removed all three startup seed calls. Retained existing
graph compatibility/reset security and explicit fixture seeds, with no stored
data purge. Removed the now-unused pypdf/docx2txt parsers. Retargeted auth/rate
checks to current endpoints and added real lifespan/route-absence coverage.
Static audit and hosted regression results will be recorded before completion.

Phase12 corrected commit c2936e4 verified by hosted run 44881901280: all jobs
successful, 450 backend/279 frontend tests, real database/full-stack/browser
checks. Transaction 89→66 distributions; CSV versions retained, dotenv settings
test passed. Broad coverage 77.68%, still below 80%. Raw resolution/installed
reports, JUnit and hash/job metadata committed; see DEPENDENCY_CLEANUP_VERIFICATION.md.

Phase13 verified source 5817fd9 / hosted run 44882037412: all jobs successful,
440 backend/279 frontend tests, actual fresh Neo4j empty and maintenance-only
before ingest, all retired routes 404, idempotent ingest and full database/browser
flows pass. Packages 89→64. Exact broad coverage 4,656/5,851 = 79.58%; rounded
80% is not treated as target completion. Raw reports, runtime JSON, browser proof,
JUnit and hash/job metadata retained. Separate owner review/merge remain pending.
Next phase addresses meaningful missing coverage before remaining research work.

## Phase 14 — research artifact-tool verification and exact coverage gate

The phase13 exact broad report was 79.58%, below target despite rounded terminal
80%. Added meaningful integration tests for official FAA codebook reproduction,
checksum refusal, malformed table rejection and 2023-only vocabulary fitting/CLI
output preservation. Added the 80% CI gate at two-decimal precision, retaining
all existing measured source scopes and no omissions. Tiny local standard-library
archive extraction reproduced all 71 official entries and fingerprints exactly;
full hosted regression and exact coverage evidence remain pending.

Phase14 source c5d279a / hosted run 44882587938 verified all jobs: 453 backend
and 279 frontend tests, real Neo4j/PostgreSQL/session and production browser
flows. All 13 new artifact-tool tests passed. Exact unchanged-scope coverage
4,744/5,851 = 81.08%; 80% gate passed (88 more covered statements, no omissions).
Raw coverage/JUnit, test names, current browser proof and job/hash/log metadata
committed under phase14 evidence. PR43 final evidence head da4ecc5 also passed
all jobs in run 44882364296. Refreshed origin/main remains 0dd86d9. Laptop still
has 24GiB free / ~12GiB available / zero swap. Next: question-conditioned 2024
selection; human/review/model/report/release gates remain explicit.

## Phase 15 — question-conditioned 2024 operating-point preparation

Added a fixed grid/provenance protocol before computing results, prefix replay
through actual answer/ask/abstain decisions, all three cohorts/strategies/strata,
shared original-report bootstrap and a separate scalar metric verifier. Selection
scoring remains downstream of the answer-key-free stopping path. Added tests for
answer priority, gain boundaries, posterior/evidence identity, actual managed
controller parity, cluster ratios/null intervals and frozen-input export.

Tiny local validation read only committed inputs: all cohorts match 389 pairs/340
originals and provenance (0.16s). The full comparison is hosted in its own bounded
one-thread workflow. No threshold is selected/activated and no 2025 source is read.
Phase14 final documentation head c41b3d2 also passed all CI jobs in run 44882911677.

Phase15 initial hosted sweep 44883542069 stopped before metrics on a strict
recomputed-prior equality check that passed on local Python 3.12. Added tight
relative/absolute roundoff tolerance (1e-12 / 1e-14) for recomputed exp/log values
only, with explicit small-noise acceptance/material-change rejection tests.
Frozen source hashes and saved trace bytes remain exact and authoritative.
Hosted revalidation is required; initial failure is not reported as success.

Phase15 source 28dcd3a verified: sweep 44883664943 and CI 44883665006 both
successful. All 4,536 rows independently replay, 389 pairs/340 originals, 1,000
cluster draws; 461 backend/279 frontend tests, 81.29% coverage and all real
database/browser flows pass. Raw full selection JSON/CSV, review proposal,
coverage/JUnit, independent verifier result and job/hash/log/browser proof saved.
A concrete async question now asks Usman to choose the research point: proposed
0.80/0.50 (23 answers:16 top-one matches/7 misses) versus 0.75/0.50 (33:21/12),
both 1.26 questions/case. No answer is inferred; no threshold activated or 2025
source read while pending. Remaining independent tasks can continue.

CSV retained-file hashes account for Git line-ending normalization: committed
CSV uses LF with identical fields; raw CRLF artifact hash is stored separately.
The verified selection JSON bytes/fingerprint are unchanged.

## Phase 16 — accepted research point and pre-test freeze

User explicitly chose “Freeze 0.80 answer / 0.50 gain (Recommended)”. Recorded
that answer with AI-assisted rationale and a selected policy that pins the exact
2024 point, decision, method/fit/schema/codebook and chronology audit. The protocol
pins the policy and retains all controls, metrics, 1000 draws and no-refit/no-
sweep rules. Preflight leaves runtime disabled and does not access 2025.

A small constant-memory audit streamed only existing frozen 2023/2024 projections
and recomputed both canonical hashes. All fit labels were submitted by April
2024; four selection labels were submitted in January 2025, latest 2 January.
Predeclared a sensitivity stratum strictly after that cutoff while retaining
all eligible occurrence-year test pairs in the primary analysis. No 2025 source
was read. Local preflight passed; hosted mutation/runtime-compatibility tests
and full regression evidence are pending. PR45 final head eb3ff53 passed all
four jobs in runs 44884119775 / 44884119746.

Retained audit_label_availability.py reproduces the timing audit exactly from
only the pinned 2023/2024 inputs, verifying their canonical projection hashes
before accepting dates. The selected policy also pins that tool and its own
preflight implementation. Reproduction and local preflight passed; the accepted
numeric choice is unchanged and 2025 remains untouched.

Phase16 source b97954d / run 44903750796 verified all jobs: 476 backend and
279 frontend tests, 81.37% coverage, real database/session/browser checks and
actual frozen-policy preflight. Hosted policy/protocol fingerprints match the
committed files; fifteen new validation/mutation/runtime-compatibility checks
pass. Raw reports, hosted preflight, browser/log/commit/hash evidence and a
self-contained verification note are retained. The accepted .80/.50 point and
pre-test freeze phase are complete; no 2025 access or runtime activation. Next
is the held-out procedure and execution, with all remaining full-goal gates kept.

## Phase 17 — verified procedure before real held-out execution

Implemented a source-hash-guarded, receipt-backed 2025 procedure around the
accepted .80/.50 point. No refit/vocabulary fit/sweep; unchanged ranker and
temporal/chain filtering; original-field simulation; all controls/budgets/strata,
fixed stopping, named-top ten-bin ECE and abstention-off at identical terminal
beliefs/questions. Added a scalar point verifier and complete interval replay.

Synthetic tests cover temporal/answer-key separation, ECE arithmetic, frozen
preflight before networking, canonical download metadata/failure cleanup and
full synthetic export plus independent replay. Normal PR events cannot download
2025. The actual job requires a one-shot label event and successful exact-head
backend/frontend/full-stack checks. Procedure hashes and the terminal comparison
definition are declared before real access; accepted numeric settings unchanged.
Historical prototype exposure is disclosed without claiming a project-wide blind
2025 year. No real 2025 archive has been opened by this preparation.

The first gated hosted attempt (44905292132) stopped before any 2025 access:
FAA 2024 now has one additional historical record. A bounded hash-only comparison
proved all original rows unchanged (2023 62,691; frozen 2024 66,080 vs current
66,081). Retained diagnosis records the extra ID and original full hashes.

Workaround: a 429KB identifier/order-only manifest reconstructs the exact frozen
history, requiring the unchanged full canonical projection hash before acceptance.
It archives the retrieved revision and records added exclusions in the pre-test
receipt. No raw CSV/narrative blob is committed, no fitting input changes, and
modified/missing original content still fails closed. A constant-memory check
reproduced both original full hashes after ignoring the new ID. Added synthetic
restoration/reordered-input/modified-content/missing-content tests plus full
export through restored history. Procedure is refrozen before any 2025 access;
accepted .80/.50 and policy fingerprint remain unchanged. Full revalidation next.

Phase17 source 5a5060b passed exact-head full CI (44905815091): 485 backend /
279 frontend tests, 5,176/6,339 = 81.65%, real database/browser checks. Ordinary
procedure preflight passed. The second one-shot run 44906082558 completed
actual 2025 evaluation and independent verification on 157 pairs/140 originals:
72 stopping tables and every saved curve/interval/ECE replayed. Primary and
predeclared chronology sensitivity agree (zero timing-overlap pairs).

At accepted .80/.50 all-attribute IG: 7 answers, 5 top-one/top-three matches,
2 misses, 150 abstentions, mean 1.4586 questions. Answered accuracy 71.43%
(cluster 95% CI 33.33–100%, 999 valid draws), coverage4.46% (1.32–8.13%).
Abstention-off uses identical terminal questions/beliefs:157 answers,31top-one/
40top-three matches. True part absent from top ten in113cases, including both
answered misses. All five correct answers are same-part cases; coded-only IG
answers none. Preserve these weak results and wide intervals without retuning.

Unmodified results/three case files/pre-test receipt/verifier report retained in
held_out_2025_v1. Raw hosted JUnit/coverage/browser/log/job/hash proof and the
failed pre-access diagnosis are retained in phase17-held-out; source projections
remain hosted artifacts. Added comprehensive HELD_OUT_VERIFICATION.md with
controls, strata, exact uncertainty, error analysis and provenance. Label removed;
ordinary CI now replays saved evidence without source downloads. No local heavy
job, staging write or runtime activation. Acceptance/knowledge bank updated;
final publication and all other full-goal gates remain.

Retained-result commit d8a8510 / CI44906671095 passed all three jobs and the
new saved-result replay step. Retained its actual job metadata and replay log,
alongside hosted artifact IDs/sizes/SHA digests. Proof hashes were checked
locally against retained bytes; each hosted result file is byte-identical and
the accepted policy SHA is unchanged. Phase17 is fully verified.

## Phase18 — publish accepted selection and frozen test

Previous goal turn completed actual evaluation and changed authoritative results:
progress, not a wait. Inspected current clean head5466ae5, plan/context/flow and
publication code before creating codex/usman-final-research-publication.

Prepared v2 fixed-source publication with actual frozen-policy/protocol and
verifier/receipt validation, all controls/strata and saved accepted-gain selection
projection. Product defaults to 2025 with saved budget curves, fixed comparisons,
chosen/off exact intervals/valid draws, ECE, time/part-change controls and proxy/
retrieval disclosures. Joint 2024 view marks the exact accepted point only in
its actual scope; earlier pre-question study remains distinct. No experiment
was rerun and all frozen source/policy bytes remain unchanged.

Prepared minimal shared-caption stage option for owner review (no shell change).
Added real-artifact integrity/component checks and expanded hosted browser
verification for accepted marker, test intervals, null controls, earlier-study
preservation and timing sensitivity in both themes/widths. Syntax checks and
one bounded stdlib actual-publication load passed; hosted verification next.

Pre-CI packaging review found that the frozen pre-access checker assumes the full
repository, whereas production Docker contains only backend under /app. Replaced
that runtime dependency with packaged-backend policy/protocol/input verification;
the full original pre-access/documentation checker remains unchanged in CI.
Added an isolated backend-only package parity/tamper test. No Docker context,
source pin, experiment result or ownership boundary was changed.

Source38ed4d7 / hosted44908576114 passed499backend/283frontend tests,81.83%
coverage and real Compose/API/browser flows. Retrieved raw reports and images.
Manual image QA found the accepted-selection screenshot clipped because its
63-row values table was open. Corrected proof capture by collapsing the table
after exact row/interval checks, and added dedicated desktop/phone accepted-
curve captures plus every test chart at390px. The fixed-test comparison table
now retains readable columns with horizontal scrolling confined to its own
container on phones. Added geometry proof for that containment, clarified
historical all-case scope and missing-answer bootstrap draws. Revalidation next.

Figure capture also now asserts the entire target lies inside the app's scroll
viewport. For a tall figure it temporarily grows capture height while preserving
the checked1280/390width, records that viewport, and restores1000/844 afterwards.
This prevents clipped element PNGs while actual phone-width/844 geometry remains
separately checked. No measurements or product behavior change.

Phase18 finalsource2af4d97/run44909092445 passed all jobs:499backend/283frontend
tests,5264/6433=81.83%, original frozen-policy preflight, saved-test replay and
real database/API/Chromium flow. Retrieved final raw reports/screenshots and
visually verified complete desktop/phone accepted curves, held-out chart and
confined comparison table. Retained proof under phase18-final-publication and
FINAL_RESEARCH_PUBLICATION_VERIFICATION.md; acceptance/knowledge updated.

## Phase19 — user-authorized merging and continued completion

User explicitly resumed and instructed “also alongside emrge existing work”.
No end-of-session handoff is requested now. Goal remains active; full requirement
scope and human/review/release gates remain. Refreshed origin/main (0dd86d9),
inspected live PR27/48 checks/mergeability and ownership/deploy contracts. PR27
foundation has exact-head green CI and compatibility evidence. User-authorized
merge is separate from absent teammate cross-review; no human approval is forged.
Initiated ordinary merge of27with exact head51196fde (no admin bypass/branch
deletion); verify GitHub result and main CI before proceeding.

User-authorized integration completed: PR27merged9ffb322; exact-head711d8ce
CI44910992549passed all jobs. Retargeted48to main; predicted merge tree matched
tested head exactly (9016f1f9). Merged48atb5c9626, preserving every dependent
commit. Verified heads28–47are main ancestors, then closed20superseded PR
records without deleting branches or claiming teammate approval. Main CI
44911321968passed; frontend production deployment7964312582succeeded. Public
https://halite-mu.vercel.app/login and /app/investigations/experiments return200;
its current JS includes the frozen research and session views and remote backend
host. This is static delivery proof, not authenticated browser acceptance.

Backend deployment44911572175built/startedb5c9626 with liveNeo4j/model/Postgres,
2079existing maintenance records and exact public revision. Its release gate
failed only because it still expected410from the now-unregistered Gitea webhook;
actual404matches tested legacy retirement. Updated both deploy expectations to
strict404, retaining all other security/version checks. Added a cross-layer test
that extracts both deployment expectations and compares the real router response.
Current release proof branch is codex/usman-release-verification. Primary root
checkout has pre-existing user changes on feat/copilot-ranking-updates; left
all of them untouched. Connected Vercel account lacks Umar-team access; used
GitHub deployment provenance and the public canonical site, keeping protection.


Release-fix source2247d17 passed hosted44911995235: 500backend/283frontend,
5264/6433=81.83%, real Compose/databases/Chromium, frozen preflight and retained
result replay. Downloaded raw JUnit/coverage/preflight and job metadata. Ordinary
exact-head merge PR49 produced29f4f59; main CI44912401813also passed. Corrected
CD44912646403is running; record its terminal outcome separately. No auth/version
check was weakened and no production research policy was activated.

## Phase20 — report and defense preparation while reviews proceed

User confirmed Usman and Muhammad Umar will complete the two independent reviews.
Provided their separate blinded HTML files and independent export instructions;
no labels or agreement are claimed. Created AI-assisted USMAN_FINAL_REPORT_DRAFT.md
covering contribution/design, access/replay/grounding, protocol, actual selection
and test results/intervals, retrieval errors, verification and prospective RQ4/RQ5.
Created USMAN_ARCHITECTURE_AND_DEFENSE.md with runtime/experimental diagrams,
practice questions, suggested presentation allocation and empty actual rehearsal
record. These drafts do not replace genuine student review, model measurements,
human labels, signatures or rehearsal. Updated panel engineering-action status,
acceptance matrix and matching knowledge context. Corrected stale security-runbook
410/re-enable descriptions to the actual unregistered404 retirement contract.


Corrected CD44912646403SUCCEEDED. Independent public reads confirmed29f4f59
on health/version, liveNeo4j/phi4-mini/PostgreSQL, maintenance-only default and
2079records. Anonymous assets/sessions/experiments401; docs/webhook404. Retained
public-backend-after.json and corrected-deploy.json. Workflow also verified the
authenticated maintenance assets response; no production user-session/browser
acceptance is inferred. Report main row cross-checked directly against committed
157/140 test counts,7answers/5matches and source hashes under phase20-report.


PR50report/release-proof source4c70a9b passed hosted44982164447 and was merged
under the user's standing merge instruction. An initial exact-head merge attempt
used an incorrectly transcribed fullSHA and was rejected without changing state;
retrieved the authoritative fullSHA and the ordinary merge succeeded.

## Phase21 — independent L4 measurement instrument

Added offline grounding_judge.py with fixed single-report prompts, full-source
preflight, exact installed model identity, strict verdict/quote validation, raw
serial journal and explicit errors. Human scoring reuses strict two-reviewer
import/consensus and reports fit/validation separately; no synthetic label or
failed-call denominator drop. The real packet contains one prompt above the
existing comparison runner's3200byte bound (max4577). Added a separate declared
8192context/6000byte judge transport; no source truncation or change to the frozen
portable model runner. Added tests for boundary/schema/quote/provenance/error,
real packet fit and actual CLI/file evaluation. No local model/install/heavy
computation or production setting change. Knowledge/context/flow/decision and
protocol updated. Hosted tests and actual model/human measurements are separate.


Phase21 source8d3abab/run44982604273 PASSED all jobs:515backend/283frontend,
5407/6587=82.09%, same six core scopes and exact80%gate, frozen preflight/saved
interval replay, real database/API/production-browser regressions. Retained raw
JUnit/coverage/preflight, job metadata and log summary. PR51ordinary exact-head
merge succeeded. PR50report merged9e135a6 and passed mainCI44982470167 and
CD44982694707. L4 actual model judgments and human metrics remain unmeasured.
Added primary-source literature companion with calibrated claims; checked PMLR,
NeurIPS and ACL primary publication abstracts/metadata, not secondary blogs.
The report's original measured-results hash crosscheck remains unchanged.


## Phase22 — actual staging-reference measurement path

Revalidated prior progress: PR52mergedd3b909a; mainCI44983303394 and deployment
44983534211 succeeded. Full objective still retains human/model/production/student
acceptance. Actual M4 access is absent, but existing private phi4-mini can supply
real staging-reference and paired no-evidence outputs. Added an explicit manual
MEASURE workflow on CI-green/currently deployed main and a standard-library glue
runner. It inspects private Docker metadata/config in memory, requires existing
image/resource/no-public-port boundaries, opens only a temporary hosted-loopback
SSH tunnel, calls the unchanged frozen runner and verifies unchanged deployment,
corpus count and container/restarts. No database writes/model pulls/settings edits
or local inference. Safe metadata/journals/failures retained; token never artifacts.
Added synthetic tests for guards, full orchestration, secret absence, token/tunnel
cleanup, postflight drift and safe SSH quoting. Documentation/knowledge updated;
actual hosted verification and real measurement remain separate gates.


Phase22 instrument sourceeeb2b77 / hosted44984026697 passed all three jobs:
531backend tests (zero failures/errors/skips),283frontend,5540/6739=82.21% core
coverage, Ruff/builds, frozen preflight/replay and real database/browser flows.
Python -S CLI help separately proved standard-library startup without installing
anything. PR53ordinary exact-head merge produced326cd885. Merged-main CI
44984283006is live; wait for terminal success and normal deployment before
manual real-reference execution. Raw source verification reports retained under
phase22-staging-reference. Do not merge a proof-only revision during the actual
measurement because its pre/postflight intentionally pins the live source SHA.


Main326cd885 passed CI44984283006 and CD44984494578. Dispatched the actual
MEASURE operation under the standing completion/merge authorization: workflow
44984568357, exact326cd885, initiallyqueued. This is a real research job, not a
synthetic test. Poll the same handle until authoritative terminal state; do not
restart merely because observation times out. No actual output or successful
measurement is yet claimed. Proof branchcodex/usman-reference-results may be
pushed for continuity but must not be merged during this pinned-source run.


Usman clarified actual Mid-I feedback in this chat: “no feedback was given like
no comments we explained our idea and they were on board no feedback was given
to change or modify something”. Recorded as student-reported no comments/no
requested modifications, not a panel transcript, signature or supervisor approval.
Updated Form10 provenance/MID-001 and acceptance status. No corrective panel
action is invented; internally identified engineering actions remain separate.

Production account access (2026-11-22): Usman explicitly authorized the dedicated
agent account and supplied a second candidate. Tried the newer candidate once
(401), then the earlier candidate (200). Authenticated profile and saved-session
listing both returned 200; explicitly logged out (200). No passwords/tokens in
project files or reports. Recorded sanitized observations in
PRODUCTION_ACCOUNT_VERIFICATION.md. This resolves account availability, not the
pending signed-in browser acceptance. Actual staging model run 44984568357 remains
in progress; keep its deployed source pinned and do not merge this proof branch
until that measurement terminates.

Prepared the dedicated public-site browser acceptance instrument and main-only
manual workflow. Local Node syntax and whitespace checks passed; no local browser
or model was started. Encrypted GitHub repository secrets HALITE_UI_TEST_EMAIL and
HALITE_UI_TEST_PASSWORD were newly configured under the user's explicit dedicated
account authorization; values were piped to GitHub without writing credential
files. No pre-existing secret was overwritten. Real hosted browser execution
remains pending the instrument's CI/merge/deployment after measurement 44984568357
terminates. The guard permits only login/refresh/logout POSTs and records no
tokens or response bodies. Knowledge/context/flow/registry/decision updated.

PR54 source0b8f7cb passed hosted CI44986105585: 531 backend tests, zero
failures/errors/skips,5540/6739=82.21% measured coverage; frontend/builds and
disposable full-stack browser job passed. Actual public browser execution remains
pending; this source's public script was syntax-checked, not run against production.
Prepared the three-page frozen2025 vector figure export using bundled ReportLab
and embedded Open Sans. Rendered all pages with Poppler and visually reviewed;
corrected first-draft font substitution/boundary crowding, then re-rendered.
Independent retained-case recount confirmed157cases,7answers,5matches,2misses,
113initial candidate misses, all5matches same-part and both answered misses
missing the initial true candidate. Raw source rows, font/generator/PDF hashes,
PNG proofs and checks retained under phase23-report-figures. Report links the PDF;
source-crosscheck report hash updated. No fitting/model/simulation/bootstrap ran.
Disk remains21GiB free; available RAM7.0GiB; swap effectively unused at this check.

Phase24: converted the retained contribution chapter/references/figures into an
editable eleven-page Word document and matching PDF, using bundled Python and
the bundled soffice override only. No new packages, browser, model or experiment
ran locally. Two native OMML equations rendered correctly; the numeric table
matches source exactly; five bibliography entries remain separate; all three
figure pages and every body page were reviewed. Corrected first-render inherited
Title blue rule and collapsed bibliography, then rebuilt/reviewed every final
page. Added page fields, image alt text and repeating table header. Accessibility
audit:0high/0medium/0low. Raw final PNGs/source/output/structural proof retained
under phase24-editable-report. Canonical chapter DOCX/PDF live in docs/fyp1-final.
This prepares student review/team integration and does not claim student authorship,
human labels, M4 results, supervisor approval or a completed defense. PR54 report
revision ab1d8ea also passed full hosted CI44986542524. Actual model run44984568357
was still authoritatively in_progress at04:54UTC; retain the source-pinned merge
hold. Do not restart it because an observation request times out.

Latest report head a942680 passed all jobs in CI44987162463; raw reports downloaded
to /tmp/halite-phase24-final-ci for the next retained release-evidence change.
The real model run remains live. Existing log workflow reads only halite-api,
which cannot show direct reference calls to Ollama. Prepared a model-progress
target that reads Docker metadata/stats and bounded logs over SSH stdin, emitting
only whitelisted state/resources and strict completed-chat time/status/duration.
No inference, deploy, restart or data writes. Unknown/raw/environment/IP fields
are excluded; activity is not attributed to individual cases. Default API log
behavior is preserved. Three focused standard-library observer tests passed,
including malformed/extra-field rejection and secret exclusion. The bundled
document Python lacks pytest; no package was installed. The tests run directly
with python3 -S/unittest and are also collected by hosted pytest. The real
reference job remains untouched and must not be restarted on an observation timeout.

Actual run44984568357 terminatedfailure05:03:22UTC after all30attempts:24responses,
6TimeoutError (all evidence-prose) at180seconds. Retained everyrawattempt, manifest,
warmup and result; independent prompt/assessment/journal/summary replay passed in
explicit failed-attempt mode with measurement_acceptedfalse. Facts10/10valid,
evidenceprose4/10valid, no-evidenceprose10/10valid; means40.28/164.56/52.99seconds
include failed attempts. No humansemanticaccuracy inferred. Original runner's
postflight was skipped by provider-error rejection; independently observed same
liveSHA/2079records and same modelcontainer/zero restarts/noOOM under4GiB/2CPU.
Read-only observer44987794344succeeded; its sanitized31servercompletion lines
include six~180sHTTP500entries. These do not independently identify researchcases.
Documented actual outcome in STAGING_REFERENCE_RESULTS.md and phase25evidence.
Prepared an explicit separate600seconddeadline study, unchanged prompts/settings/
model/resources, workflow ceiling330minutes. Moved postflight before collected-
error rejection and retain final safe metadata; failed runs still fail acceptance.
The previous merge hold is released because its specific run is terminal. Merge
only after new exact-head CI passes; verify the real public site before starting
any next source-pinned measurement. No silent case retry or deadline pooling.

Sourcec330480 passed full CI44988236394:534backend tests, zero failures/errors/
skips,5543/6742=82.22% measured core coverage; frontend/builds and actual disposable
Neo4j/PostgreSQL/API/Chromium proof all passed. Ordinary exact-head merge of PR54
produced db574acadd4caf5cf60be45559708c82319711a6 at05:14:18UTC. No admin bypass or
branch deletion. Merged-main CI44988523496 is live; wait for its success and normal
CD before claiming deployment or dispatching the public browser. The public-site
workflow is registered active and encrypted dedicated-account secrets already
exist. New proof branch codex/usman-public-verification starts from merged main;
root checkout's unrelated work remains untouched. Source/merge/XML receipts are
retained under phase26-public-release. No new source-pinned model run has started.

Merged-main CI44988523496 and normal deploy44988762837 succeeded; independent
publichealth confirmed exactdb574ac/Neo4j/livephi4/PostgreSQL/2079records. Dispatched
manualVERIFY under existing dedicated-account authorization; actual browser run
44988921561passed05:20:32UTC. Allsix screenshots visually reviewed and hash-checked;
real login/deep-link/research source parity/home/history/refresh/logout and326px
phone main area verified. Zero pageerrors/prohibitedwrites. No password/token
artifacts. Source, main, deployment, health and browser evidence retained under
phase26-public-release and PUBLIC_BROWSER_VERIFICATION.md. The dedicated account
had zero investigations, so this proves empty/read flow, not production creation/
turn/closure/print. Next verify one clearly labelled account-owned test lifecycle
and actual model reply before starting another source-pinned reference run.

Phase27 actual lifecycle probe completed against db574ac using the dedicated
authorized account and one labelled synthetic session cbc8d780-9af2-4144-8a21-
27cf8209c063. Create201, one turn200, independent exact response/belief replay,
closure, closed-write409 and reportHTML200 all passed. No outcome part or real
finding was recorded; the named-outcome training filter excludes this test case.
Corpus/source remained unchanged and logout was confirmed. The overall live-
prose gate intentionally failed: provider timeout, llm_status unavailable, marked
fallback, 158.71seconds. Separate actual quick baseline also timed out, returning
ranking/fallback after131.05seconds. Raw attempts remain under phase27; neither
is called a live model success. No local model or browser was launched.

Prepared the bounded runtime fix under the accepted vertical ownership handoff
DEC-20261120/CONTRACTS: Usman owns the Copilot route and model adapter. The old
actual prompt reconstructed to15,259bytes/2,400output tokens. The final pure
builder uses at most2,048bytes/192tokens and three prioritized excerpts, preserving
all full response evidence and deterministic ranking/case state. It records and
warns about actual supplied versus available IDs; citation and sentence checks
use the true model boundary. Structured answers discard prior model provenance.
A larger all20metadata prototype was unexecuted and is marked superseded; it used
3,129bytes before any narrative, so it could not meet the intended small context.
Quick JSON retains source lists/schema, shorter wording/512tokens and safe
malformed-structure fallback; complete plain legacy prose is preserved. Token-
cutoff prose is rejected in both providers; JSON classification is unchanged.
Frozen methods/results/comparison generation remain untouched. Five pure local
tests, AST checks, Node syntax and baseline replay passed without installs;
hosted API/provider/coverage/full-stack and new live model outputs remain pending.
The browser verifier additionally prepares explicit saved-case read/reload/print
mode with A4PDF output; no browser session/model mutations are added.

PR55 source8c745a9 / CI44992153774 passed frontend and disposable full-stack
checks. Backend ran549tests with one failure: the new cutoff guard changed the
established empty-content diagnostic for a Groq response with both contentNone
and finish_reason length. Retained raw JUnit/coverage and fixed validation order
in both providers: empty content retains its original diagnostic; only nonempty
truncated prose reaches the new guard. The existing regression test is unchanged.
All other548backend cases passed, including new source-boundary, malformed-JSON,
classifier-format and structured-answer provenance checks. New exact-head CI is
required; no merge, deployment or successful live model fix is claimed yet.

PR55 corrected source b9bad63 passed CI44992570766:549 backend tests,
zero failures/errors/skips,5629/6815=82.60% measured coverage; frontend/build
and real-graph/full-stack/browser passed. Exact-head ordinary merge authorized
by the user produced11beed1f2b050057942ba31321ce7f2e7b0bf80f at06:15:57UTC.
Retained raw receipts/XML in phase28-bounded-runtime-release. Main CI, actual
deployment and post-release live-model/closed-case browser checks remain pending.

Main CI44992947098/deploy44993176097 passed, public exact11beed1/2079.
Actual fresh session74c792ce-510c-4c60-addb-a7f441435246 verified lifecycle
but prose again timed out after154.35s total; compact prompt was2042bytes/192tokens.
Never mark live prose fixed. Hosted browser44993544541 passed real saved-case
replay/closed guard/phone layout/one-click print plus public read checks; model
unavailable is honestly rendered. Raw API/model/browser artifacts retained.

Visual review of all seven hosted screenshots passed. All three actual PDF
pages inspected: zero-margin page boundary clips the top of a narrative line.
Prepared own report CSS correction:A4/16mm margins, fitting evidence entries
together, widow/orphan control; hosted export honors CSS page size. Original
PDF retained; new deployed export/review required. No claim of print visual
acceptance before correction. Model transport investigation remains open.
