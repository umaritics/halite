# Halite FYP — corrected Cursor handoff

Updated 2026-10-17 after PR #7 CI. This is the current handoff for an agent
that has not seen the previous sessions. It reconciles Claude’s supplied
handoff with the repository and work completed after that document was written.

## 0. Start here

Do not restart round 3 from `main`.

```text
git fetch origin
git checkout feat/mid1/analysis-cost-cascade
git pull --ff-only origin feat/mid1/analysis-cost-cascade
```

- Current round-3 PR: https://github.com/umaritics/halite/pull/7
- PR #7 base: `feat/mid1/confidence-and-corrections` (stacked because PR #6 is still open)
- Current implementation commit: `456c22e`
- Parent PR: https://github.com/umaritics/halite/pull/6
- Do not merge either PR; the user merges.
- If PR #6 is merged while you work, update/retarget PR #7 carefully; do not
  rebuild the feature or force-push.

Read `AGENTS.md`, `knowledge/README.md`,
`knowledge/context/modules/conflict_engine.md`,
`knowledge/flows/FLOW-conflict-review.md`, and
`knowledge/decisions/DEC-20261017-analysis-cost-cascade.md` before edits.

## 1. Verified repository state

### Pull requests and CI

PR #6 is open, clean, and green. It contains confidence/correction state,
fleet-wide Service Records, corrections UI/API, migration/backfill work, and a
Neo4j service in CI.

PR #7 is open and all checks are green:

```text
Backend tests (Python 3.11)          PASS — 194 passed on real Neo4j CI
Frontend tests and build (Node 20)  PASS
Docker Compose real-graph smoke     PASS
Vercel                              PASS
```

Local verification for PR #7:

```text
backend: 171 passed, 23 skipped (the skips require Neo4j)
frontend: 126 passed
Vite production build: passed, 854 modules transformed
```

The CI run is https://github.com/umaritics/halite/actions/runs/39044958072.

### Copilot status correction

Diagnostic Copilot is already merged into `main` through PR #5 at merge commit
`21bd629`. The implementation commits are `0968651`, `b5b6de3`, and
`b77b743`.

The supplied handoff incorrectly left this merge status unverified. It also
named `docs/mid1/18_diagnostic_copilot_demo_scenarios.md`, but that file is not
tracked in the current repository. The tracked evidence is
`docs/mid1/17_diagnostic_copilot_evidence.md`.

The later Copilot-polish request is not implemented on this branch. Current
code still exposes internal prompt concepts such as `RANKING_DELTA`, uses
`fleet_match` internally, and does not have `remark-gfm` installed. Treat GFM
tables, marker stripping, conservative record-count claims, and generic-token
ranking as a separate future Copilot change. Do not mix it into PR #7.

## 2. What PR #7 has implemented

The implementation was based on the original round-3 prompt, which explicitly
required `legacy` to remain the default and a 90% daily budget boundary. A
later Claude handoff supplied an expanded replacement prompt; its additions are
listed separately in section 3.

Implemented and tested:

1. Usage metering
   - Cache and record metadata contain model, method, pass count, every vote,
     agreement, timestamp, and prompt/completion/reasoning/total tokens when
     Groq returns them.
   - Old flat cache entries normalize safely.
   - Neo4j stores votes as JSON text because node properties cannot store maps.

2. Deterministic free screen
   - New module: `backend/services/conflict_screen.py`.
   - Features: meaningful-text containment, Jaccard, and exact
     part/JASC/location equality.
   - Boilerplate and `SUPPLEMENTAL REPORT FOR <ID>` are removed.
   - No same-day feature/filter was added.
   - Cascade ranking uses containment first and preserves the legacy
     score/date/ID order as the stable tiebreak.
   - Pre-registered threshold: `0.79`.

3. Adaptive voting
   - Two initial passes; agreement stops at two.
   - Disagreement buys three more passes, for five total.
   - A persistent split routes to review only in cascade mode.
   - Confidence scales the classification signal by vote agreement, not the
     number of passes.

4. Persistent daily budget
   - New module: `backend/services/analysis_budget.py`.
   - Tracks requests and tokens per model per UTC day in an atomic state file.
   - Cache hits do not debit budget.
   - `POST /maintenance/analysis/run` returns `stopped_reason` and
     `budget_remaining`.
   - `backfill_conflict_scores.py --until-budget` resumes explicit unscored
     records and stops cleanly.

5. Mode and transparency
   - `MAINT_ANALYSIS_MODE=legacy|cascade` exists.
   - Default is still `legacy`.
   - `/analysis/status` includes `by_method`.
   - Service Records and Asset History confidence tooltips describe screen,
     two-pass model, and escalated model results.

6. Documentation honesty
   - `evaluate_conflict_detection.py` no longer presents its literal
     full-corpus counts as computed output.
   - Visible warnings were added to `docs/evaluation_results.md` and
     `docs/misdiagnosis_density.md`.
   - The non-reproducible figures remain preserved as historical evidence:
     121, 117, 4, 1,617, and 1,958. The 0.762 F1 belongs to saved
     `openai/gpt-oss-120b` pair outputs, not the current configured model.

7. Evidence and engineering memory
   - `docs/mid1/21_analysis_cascade_evidence.md`
   - `knowledge/decisions/DEC-20261017-analysis-cost-cascade.md`
   - conflict-engine context, flow, registry, and index updated.
   - Three temporary mutation checks were run and reverted.

No live Groq call, full analysis, held-out-year inspection, staging migration,
or staging graph write occurred.

## 3. Expanded handoff requirements not yet implemented

Claude’s later “replacement” prompt added requirements that were not in the
task used to build PR #7. Do not assume these exist:

### A. Interactive reserve / 70% cap

Current code stops analysis at 90% of configured request/token limits through
`MAINT_BUDGET_UTILIZATION=0.90`. The expanded prompt requests a configurable
30% interactive reserve, meaning analysis should stop at 70%.

If the user confirms the expanded requirement, replace the generic utilization
setting or reinterpret it clearly, update tests/DEC/evidence, and preserve
backward-compatible env behavior. Add tests proving both request and token
reserve boundaries.

### B. Ordered model fallbacks

`MAINT_MODEL_FALLBACKS` is not implemented. `GROQ_API_KEY_FALLBACK` is an
existing fallback key, not an ordered list of fallback models. The repository
default model is `openai/gpt-oss-20b` (not 120b); the local ignored `.env` was
observed using `qwen/qwen3.8-27b`.

If model fallbacks are added, one classification must use one model for all its
passes. Never mix votes across models. Persist the chosen model and budget each
model independently. Verify current official limits before setting defaults.

### C. Aircraft-first queue and aircraft coverage

Not implemented. Current API/backfill selection remains record-oriented and
chronological. Missing pieces from the expanded prompt:

- finish one aircraft oldest-to-newest before starting another;
- priority: configured demo tails, then most ground-truth pairs, then cheapest
  estimated analysis cost;
- `aircraft_total` and `aircraft_fully_analysed` in `/analysis/status`;
- Review Queue coverage line such as “N of 118 aircraft fully analysed”;
- fake-LLM tests for ordering and method/status counts.

This is the largest remaining offline code item. Demo documentation identifies
`813SK` as the primary aircraft and `163AA` for a review item. The supplied
handoff also named `811NN`, but that tail was not found in the checked demo
script; verify it before adding a default list.

### D. Default-mode conflict

The implemented DEC and original prompt require default `legacy` until live
round-four validation. The expanded prompt says default `cascade` if offline
retrieval gates pass. The gates did pass, but classification/token behavior is
not live-validated.

Do not flip this silently. Ask the user which instruction wins, then update the
DEC, config, env example, golden tests, evidence, and handoff together.

### E. Token projections

Still unavailable. The inherited 63-entry cache has majority results only and
no usage/votes. The “about 3,000 tokens per classification / four weeks” text
in the supplied handoff is explicitly a rough estimate, not verified evidence.
Round four must measure actual tokens.

## 4. Reverified corpus and cascade numbers

Input files are gitignored and must be obtained from the user or regenerated:

- `backend/data/processed/sdr_poc_corpus.csv`
- `backend/data/processed/ground_truth_pairs.csv`

Real offline measurement on the local files:

| Measure | Result |
| --- | ---: |
| Records / aircraft | 2,079 / 118 |
| Records with any candidate | 1,835 |
| No-candidate records | 244 |
| Raw positive-score pairs | 32,457 |
| Pairs after 25 cap | 19,119 |
| Legacy top-1 requests | 1,835 × 5 = 9,175 |
| Known true priors retained at screen threshold | 141/141 |
| Legacy true-prior top-1 | 124/141 |
| Containment-first true-prior top-1 | 136/141 |
| Deterministically screened model-eligible records | 804/1,835 = 43.8% |
| Remaining model classifications | 1,031 |
| Cascade request low/high | 2,062 / 5,155 |

At a 90% request cap, request-only projections are 3–6 UTC quota days rather
than 11. Token days are **NOT RUN / UNVERIFIED**. The cascade does not yet
prove the desired 10x token reduction.

Provider table checked 2026-10-17:
https://console.groq.com/docs/rate-limits. It listed 30 RPM, 1,000 RPD, 8,000
TPM and 200,000 TPD for `qwen/qwen3.8-27b` and
`openai/gpt-oss-20b`; organization-specific console limits remain authoritative.

## 5. Important product/repository facts

- Halite ingests FAA Service Difficulty Reports, represents aircraft service
  history in Neo4j, classifies correction relationships, and supports diagnosis.
- Stack: FastAPI/Python 3.11, Neo4j, React/Vite/Tailwind/Vitest, Groq.
- Staging API: https://dev1.corp.curatech.pk/halite-api.
- Runtime claims require `/api/health` to report `graph_mode=neo4j`,
  `llm_mode=live`, and the maintenance corpus loaded.
- Docker Desktop/WSL was broken locally. CI supplies Neo4j 5 Community.
- Secrets are in ignored env files. Never print or commit them.
- `MAINT_CONFIDENCE_THRESHOLD` remains 0.50. Do not change classifier prompts,
  shared routing, or threshold to beautify the demo.
- Do not write to shared staging without explicit approval in the active
  conversation.
- Do not touch Copilot, Graph, or unrelated pages while finishing PR #7.
- `DELETE /api/graph/reset` remains an unauthenticated destructive risk and was
  not touched.
- The graph page’s 2,000-node cap, CI lint, release tagging, dependency
  advisories, and sibling-event false corrections are later tasks.

## 6. Suggested next sequence for Cursor

1. Pull PR #7 and run the current suites before editing.
2. Confirm with the user whether the expanded replacement requirements should
   be added to PR #7 and whether cascade may become the default before live
   validation.
3. If confirmed, implement the reserve, aircraft-first queue/status/UI line,
   and optional model fallbacks with fake-LLM tests. Keep scope to conflict
   analysis and the tiny coverage UI.
4. Rerun the 2,079-record offline measurement. Do not inspect held-out years.
5. Run backend/frontend/build, at least three mutation checks, push, and wait
   for real-Neo4j CI.
6. Update `docs/mid1/21_analysis_cascade_evidence.md` with exact output and a
   clear NOT RUN / UNVERIFIED list.
7. Round four, only after approval: bounded live token/quality measurement,
   priority-aircraft run on local/scratch graph, then a proposed staging
   sequence. No staging write without explicit approval.

## 7. Commands

```text
cd backend
python -B -m pytest -q -p no:cacheprovider

cd ../frontend
npm test
npm run build
```

Offline corpus measurement:

```text
cd backend
python -B scripts/measure_analysis_cost.py \
  --corpus <local>/backend/data/processed/sdr_poc_corpus.csv \
  --ground-truth <local>/backend/data/processed/ground_truth_pairs.csv
```

## 8. Safe and unsafe claims

Safe with scope stated:

- 2,079 records, 118 aircraft, 141 FAA-authored supplemental pairs;
- offline screen/ranking/request figures in section 4;
- local and CI test counts in section 1;
- archived 0.762 F1 only as the saved 350-pair
  `openai/gpt-oss-120b` result at threshold 0.50.

Do not present as current/full-corpus product results:

- 121 detected;
- 117 auto-resolved;
- 4 review;
- 1,617 no-candidate;
- 1,958 remaining;
- any token/day or total-duration estimate for cascade;
- any live model, staging migration, or full-run result not actually executed.

## 9. Files most relevant to the remaining work

| Area | Files |
| --- | --- |
| Cascade | `backend/services/conflict_engine.py`, `conflict_screen.py` |
| Metering/budget | `backend/services/groq_service.py`, `analysis_budget.py` |
| Queue/API | `backend/api/routes/maintenance.py`, `backend/scripts/backfill_conflict_scores.py` |
| Stores | `backend/graph/queries.py`, `backend/graph/memory_store.py` |
| UI | `frontend/src/components/ConfidenceBar.jsx`, `pages/ReviewQueue.jsx` |
| Tests | `backend/tests/test_conflict_cascade.py`, `test_api_maintenance.py`, `test_graph_maintenance.py`, `frontend/src/test/ServiceRecords.test.jsx`, `ReviewQueue.test.jsx` |
| Evidence | `docs/mid1/20_analysis_cost_report.md`, `21_analysis_cascade_evidence.md` |
| Decision | `knowledge/decisions/DEC-20261017-analysis-cost-cascade.md` |

Keep final status messages to 15 lines or fewer. State exactly what was run and
what remains unverified.
