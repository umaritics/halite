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
