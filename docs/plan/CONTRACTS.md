# Halite shared contracts

Read this file at the start of every coding session, after `AGENTS.md` and before your own agent guide.
It is the agent-facing half of the Halite Master Plan (20 November 2026). Where this file and an older
document disagree, this file wins. Where this file and the running code disagree, stop and tell your human.

- Base commit for every fact below: `origin/main` at `ac5aa66` (16 November 2026).
- Scope is unchanged: nine modules, thirteen objectives, five research questions.
- What changed: ownership moves from layers (frontend, backend) to three full-stack verticals.

---

## 1. Verticals and owners

| Vertical | Owner | Sub-problem | Backend package | Route prefix | Frontend folders |
| --- | --- | --- | --- | --- | --- |
| V1 Retrieval and Ranking | Muhammad Umar | Find the right past cases and rank candidate parts | `backend/retrieval/`, `backend/evaluation/` | `/api/retrieval/`, `/api/evaluation/` | `features/retrieval/`, `features/evaluation/`, `features/graph/` |
| V2 Record Integrity | Shahmeer Atif | Decide which reports still stand | `backend/integrity/` | `/api/integrity/` plus the existing `/api/maintenance/` review, analysis, corrections and ingest routes | `features/integrity/`, `features/intake/`, `features/assets/`, plus the shell, `features/auth/` and `features/admin/` |
| V3 Investigation Sessions | Muhammad Usman Al Haq | Answer, ask or abstain, and ground every sentence | `backend/investigation/` | `/api/sessions/` plus the existing `/api/maintenance/diagnose`, `/copilot/turn`, `/chat` | `features/investigation/`, `features/home/` |

One project, three interdependent sub-problems. V2 decides validity, V1 ranks using only valid evidence,
V3 turns the ranking into a decision, and closed sessions return as labelled cases.

Shared duties:

| Duty | Owner |
| --- | --- |
| Staging VM, deploys, graph backups, corpus builder | Umar |
| Backend preparation, CI quality (lint, coverage), Panel Action Register (Form 10) | Usman |
| Frontend preparation, application shell and design system, report editing, disclosure sheet (Form 13) collation | Shahmeer |

The poster is already made. It still needs the handbook format check and the supervisor's approval.

---

## 2. File ownership at the base commit

An agent edits only files owned by its human. Anything else needs a pull request reviewed by the owner.

### Backend

| Path | Owner | Note |
| --- | --- | --- |
| `services/diagnostic_retrieval.py` | Umar | Frozen as baseline B0, then replaced by `backend/retrieval/` |
| `scripts/fetch_sdr_data.py` | Umar | Handed over from Usman; becomes the multi-year corpus builder |
| `scripts/benchmark_local_llm_gt.py` | Shahmeer | Handed over from Umar; the starting point for the masked benchmark |
| `api/routes/graph.py` | Umar | `/api/graph/overview` feeds the graph page |
| `api/routes/ops.py`, `scripts/vm/`, `docker-compose.vm.yml`, `.github/workflows/deploy-staging.yml`, `.github/workflows/fetch-staging-logs.yml` | Umar | Staging |
| `api/security.py`, `services/auth_service.py`, `api/routes/auth.py`, `db/session.py`, identity models | Umar until January, then Shahmeer (tenancy is his FYP-II work) | Frozen in December; bug fixes only |
| `services/conflict_engine.py`, `services/conflict_screen.py`, `services/analysis_budget.py`, `services/analysis_state.py` | Shahmeer | Handed over from Usman, who wrote them. Become a thin facade over `backend/integrity/` |
| `agents/maintenance_agent.py`, `domains/`, `api/routes/maintenance.py` | Shahmeer | Handed over from Usman. Existing route contracts are frozen |
| `scripts/backfill_conflict_scores.py`, `scripts/evaluate_conflict_detection.py`, `scripts/measure_*.py`, `scripts/migrate_conflict_analysis_state.py`, `scripts/verify_confidence_corrections.py` | Shahmeer | Handed over from Usman |
| `scripts/verify_mid1_runtime.py` | Usman | The CI smoke test |
| `.github/workflows/ci.yml`, `docker-compose.yml` | Usman | CI |
| `api/routes/diagnostics.py`, `services/citation_validation.py`, `services/groq_service.py` | Usman | He wrote the Copilot routes; the model adapter comes over from Umar |
| `api/router.py`, `config.py`, `.env.example`, `main.py`, `requirements.txt`, `tests/conftest.py`, `graph/schema.py` | Shared; Usman is steward | Additive edits only, in your own clearly marked block |
| Legacy software domain: `api/routes/{chat,decisions,ingest,alerts,webhooks}.py`, `agents/{code,document,decision,gitea,base}_agent.py`, `services/context_builder.py`, `domains/software.py`, `graph/invalidation.py`, root-level `check_*.py`, `find_demo_record.py`, `top_assets.py`, `demo_candidate_pairs.py`, `verify_t6.py` | Usman deletes them in the backend preparation pull request | Nobody adds to them |

### Frontend (paths after the frontend preparation pull request)

| Path | Owner |
| --- | --- |
| `src/app/` (registry and shell), `src/components/ui/`, `src/api/http.js`, `src/index.css`, `tailwind.config.js`, `App.jsx`, `Sidebar.jsx` | Shahmeer |
| `src/features/auth/` (Login, AcceptInvite, AuthContext, ProtectedRoute), `features/admin/` (TeamAccess, Settings) | Shahmeer |
| `src/features/investigation/` (today: `pages/Diagnostics.jsx`, `components/DiagnosticEvidenceInspector.jsx`, `components/CopilotMarkdown.jsx`, `utils/diagnostic*.js`), `features/home/` | Usman |
| `src/features/integrity/` (today: `pages/ReviewQueue.jsx`), `features/intake/` (today: `pages/MaintenanceIngest.jsx`, `components/CsvUploader.jsx`, `components/IngestResult.jsx`), `features/assets/` (today: `pages/Assets.jsx`, `pages/AssetHistory.jsx`, `pages/ServiceRecords.jsx`) | Shahmeer |
| `src/features/retrieval/`, `features/evaluation/`, `features/graph/` (today: `pages/Graph.jsx`, `components/GraphViewer.jsx`, `utils/graphScope.js`) | Umar |

---

## 3. The preparation window, 20 to 24 November

Only these three pull requests touch shared files. Until they merge, everyone else works in new files only.

### 3.1 Backend preparation (Usman)

No behaviour change in any maintenance route. CI must stay green.

1. Delete the legacy software domain listed above, its tests (`tests/test_regression_software.py`) and the
   `seed_demo_data` startup call in `main.py`. Keep `/api/graph/overview`.
2. Split `graph/queries.py` (1,184 lines) into a package `graph/repo/`:
   `core.py` (the `GraphRepository` class shell, assets, records, shared helpers),
   `retrieval.py` (Umar's queries), `integrity.py` (Shahmeer's queries). Use mixins so
   `GraphRepository` keeps its public method names. Do the same for `graph/memory_store.py`.
3. Turn `db/models.py` into a package `db/models/` with `identity.py` (the current five tables, unchanged)
   and three empty modules `evaluation.py`, `integrity.py`, `sessions.py`, all imported by `db/models/__init__.py`
   so `Base.metadata.create_all` sees new tables.
4. Create one empty router file per vertical and register each once in `api/router.py`:
   `api/routes/retrieval.py`, `api/routes/evaluation.py`, `api/routes/integrity.py`, `api/routes/sessions.py`.
   Each exposes only `GET /<prefix>/summary` returning the summary shape in section 4.6 with an empty `stats` list.
5. Add three marked blocks to `config.py` and `.env.example`: `# --- RETRIEVAL_ ---`, `# --- INTEGRITY_ ---`,
   `# --- SESSION_ ---`.
6. If this runs past 24 November, cut step 1 and ship steps 2 to 5. Parallel work depends on those.

### 3.2 Frontend preparation (Shahmeer)

No behaviour change. All existing tests stay green.

1. Delete dead code (866 lines, no live or test imports): pages `Chat`, `Decisions`, `Ingest`, `Alerts`;
   components `AlertBanner`, `ChatMessage`, `DecisionCard`, `FileUploader`, `DomainSwitcher`, `icons/OctahedronIcon`;
   `hooks/useChat.js`; `DomainContext`; the legacy groups in `api/client.js`
   (`chatAPI`, `decisionsAPI`, `ingestAPI`, `alertsAPI`, `domainsAPI`).
2. Move the axios instance and interceptors (`api/client.js` lines 1 to 89) to `src/api/http.js` and add a
   request timeout. Each feature owns `src/features/<name>/api.js`. `api/client.js` stays as a re-export barrel
   so existing `vi.mock('../api/client')` factories keep working.
3. Each feature exports `manifest.jsx`: `routes: [{path, element, roles}]` and
   `nav: [{to, label, icon, order, roles, useBadge}]`. `src/app/registry.js` collects them with
   `import.meta.glob('../features/*/manifest.jsx', {eager: true})`. `App.jsx` and `Sidebar.jsx` render from the
   registry and are not edited again.
4. Split `pages/Diagnostics.jsx` (1,581 lines, eight components) and `pages/ReviewQueue.jsx` (550 lines) into one
   file per component inside their feature folders.
5. Add `src/components/ui/` primitives: `Button`, `Tabs`, `PageHeader`, `ErrorCard`, `EmptyState`,
   and one `ErrorBoundary` around the routed outlet.
6. Add one chart library (Recharts). Nobody adds a second one.
7. All new pages stay under `/app/*`, so `vercel.json` and `VercelRouting.test.js` are untouched.

### 3.3 Data foundation (Umar)

See the corpus contract in section 4.4. Also move staging caches off the 64 MB `tmpfs` at `/app/data`
(`docker-compose.vm.yml` line 85) to a named volume.

---

## 4. Interfaces

Each interface has an implementation that works today and a better one that arrives behind a setting.
Code against the interface so nobody waits.

### 4.1 Validity of a report (owner: Shahmeer)

Today a consumer checks `record.get("status") == "superseded"`. That string is unreliable: it is overwritten
when the record is re-processed (`services/conflict_engine.py` lines 724 to 725). The target is link-based.

```python
# backend/integrity/validity.py
def superseded_by(graph_repo, record_ids: list[str]) -> dict[str, str]:
    """Map each superseded record_id to the record_id that supersedes it. Reads SUPERSEDES links."""

def is_current(record: dict, superseded: dict[str, str]) -> bool:
    """True when no link supersedes this record."""
```

Until `validity.py` lands, consumers wrap the status check in one local function so the swap is one line.

Link contract:

```
(new:ServiceRecord)-[:SUPERSEDES {scope, confidence, rationale, created_at,
                                 method, model_version, decided_by, decided_at}]->(old:ServiceRecord)
```

`scope`, `confidence`, `rationale`, `created_at` keep their current meaning. `method` is one of
`explicit_citation`, `model`, `human`.

### 4.2 Ranked parts with evidence (owner: Umar)

Today V3 calls `build_diagnostic_context` / `build_copilot_context` and `rank_diagnostic_checks` /
`rank_copilot_checks` in `services/diagnostic_retrieval.py`. The target:

```python
# backend/retrieval/service.py
def rank(graph_repo, *, asset_id: str | None, symptoms: list[str], observations: list[str] = (),
         ruled_out: list[str] = (), as_of: str | None = None, mode: str | None = None, k: int = 10) -> dict
```

Return shape (existing `ranked_checks` keys are kept; everything else is additive):

```json
{
  "mode": "hybrid_rrf",
  "ranker_version": "v1-rrf",
  "hypotheses": [
    {"part_name": "PROXIMITY SENSOR", "jasc_code": "3230", "score": 0.0431, "rank": 1,
     "evidence_count": 4, "evidence_record_ids": ["AALA2025..."],
     "sources": ["asset_history", "same_model", "fleet"],
     "breakdown": {"bm25": 0.021, "dense": 0.017, "graph": 0.005, "validity_penalty": 0.0}}
  ],
  "evidence": [
    {"record_id": "AALA2025...", "asset_key": "813SK", "scope": "same_aircraft",
     "occurred_at": "2025-03-01", "submitted_at": "2025-03-02T10:24:57.400-05:00",
     "part_name": "PROXIMITY SENSOR", "jasc_code": "3230", "text": "...",
     "is_superseded": false, "superseded_by": null,
     "scores": {"bm25": 12.3, "dense": 0.71, "fused": 0.031}}
  ],
  "context_size": {"asset_records": 30, "candidate_records": 200}
}
```

- `mode` is one of `mid_heuristic`, `mid_fixed`, `bm25`, `dense`, `graph`, `hybrid_rrf`, `hybrid_fitted`.
  The default comes from the setting `RETRIEVAL_MODE`, which starts as `mid_heuristic`.
- `scope` is one of `same_aircraft`, `same_model`, `fleet`.
- V3 reaches the ranker only through `backend/investigation/ranker_port.py`, which calls
  `retrieval.service.rank` when it can be imported and the mode is not `mid_heuristic`, and the mid functions otherwise.

### 4.3 Sessions and outcomes (owner: Usman)

Tables `diagnostic_sessions`, `session_turns`, `session_snapshots` in PostgreSQL. Other verticals never write to
them. They may read closed sessions with an outcome through `GET /api/sessions?status=closed&has_outcome=true`
to harvest labelled cases.

### 4.4 Corpus files (owner: Umar)

All under `backend/data/processed/`, git-ignored, rebuilt by one command from the FAA source
`https://external.apic4e.faa.gov/sdrs/retrieve/SDR-{year}.csv`.

| File | Columns |
| --- | --- |
| `corpus_2023.csv`, `corpus_2024.csv`, `corpus_2025.csv` | The twelve existing columns (`OperatorControlNumber`, `DifficultyDate`, `SubmissionDate`, `RegistryNNumber`, `AircraftMake`, `AircraftModel`, `AircraftSerialNumber`, `PartName`, `PartCondition`, `PartLocation`, `JASCCode`, `Discrepancy`) plus `NatureOfConditionA`, `PrecautionaryProcedureA`, `StageOfOperationCode`, `HowDiscoveredCode` |
| `correction_pairs.csv` | `superseded_record_id`, `superseding_record_id`, `tail_number`, `year`, `submission_gap_days`, `part_change` (`same`, `named_to_named`, `unknown_to_named`, `named_to_unknown`), `jasc_change` |
| `splits.json` | `{"fit": [2023], "select": [2024], "test": [2025]}` |
| `sdr_poc_corpus.csv`, `ground_truth_pairs.csv` | Unchanged. They remain the staging corpus (2,079 reports, 141 pairs). |

Reference counts, measured on the raw FAA files on 20 November 2026 before text de-duplication:

| Year | Rows | Aircraft | Citations found | Valid pairs |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 62,691 | 8,136 | 432 | 428 |
| 2024 | 66,080 | 8,325 | 401 | 396 |
| 2025 | 67,653 | 8,552 | 163 | 157 |
| Total | 196,424 | 12,244 distinct | 996 | 981 |

A valid pair means the cited ID exists, is a different report, and shares a non-empty tail number.
The builder's de-duplication will lower these slightly (2025 becomes 66,658 rows and 141 pairs in the existing profile).
If the builder's numbers are far from these, stop and investigate before anyone uses the files.
Write the real numbers to `docs/dataset_profile.md`.

Facts about the pairs that every vertical must respect:

- All 981 corrections carry the **same `DifficultyDate`** as the report they correct.
- By `SubmissionDate` the correction arrives after a median of 5.1 days (10th percentile 1.0, 90th 24.0, maximum 203.3), never before.
- `SubmissionDate` looks like `2025-01-02T09:45:26.140-05:00`. Parse it as a timezone-aware datetime. Never compare it as a string.
- In 787 of 981 pairs the correction repeats at least 80% of the original's tokens and appends the finding after
  `SUPPLEMENTAL REPORT FOR (<id>):`. Originals often end with `**SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN)`.
- Part change: 314 pairs go from one named part to a different named part, 375 replace `UNKNOWN`/`NONE` with a named part, 292 keep the part.
- `NatureOfConditionA`, `PrecautionaryProcedureA`, `StageOfOperationCode` and `HowDiscoveredCode` are filled in 100% of rows.
  `ComponentName` is filled in about 1% and is not usable.

### 4.5 Model adapter (owner: Usman)

`services/groq_service.py` line 70 sends `response_format: {"type": "json_object"}` on every call of the
OpenAI-compatible path, which breaks prose replies on the local model. The target:

```python
GroqService.chat(messages, system_prompt=None, max_tokens=2048, json_mode: bool = False) -> str
GroqService.extract_json(prompt, system_prompt=None, max_tokens=800) -> str   # always json_mode=True
```

`response_format` is sent only when `json_mode` is true. Both paths have a test with `httpx` mocked.
Shahmeer's classifier keeps calling `extract_json` and is unaffected.

### 4.6 Summary endpoints for the home dashboard

`GET /api/retrieval/summary`, `GET /api/integrity/summary`, `GET /api/sessions/summary` each return:

```json
{"title": "Record integrity", "link": "/app/integrity",
 "stats": [{"label": "Awaiting review", "value": 87, "hint": "was 494 before calibration"}]}
```

The dashboard hides a widget whose endpoint fails. No vertical waits for another's widget.

---

## 5. Naming

| Thing | V1 Umar | V2 Shahmeer | V3 Usman |
| --- | --- | --- | --- |
| Neo4j labels | `Part`, `System`, `AircraftModel` | `FaultCase` | none |
| Neo4j relationships | `INVOLVES` (record to part), `CONCERNS` (record to system), `OF_MODEL` (asset to model) | `SUPERSEDES` (existing, gains properties), `NOT_SUPERSEDES`, `PART_OF` (record to case) | none |
| Properties added to `ServiceRecord` | `embedding`, `embedding_model` | `proposed_prior_id`, `cited_record_ids`, `integrity_p`, `integrity_model_version` | `stage_of_operation`, `how_discovered`, `nature_of_condition`, `precautionary_procedure` |
| PostgreSQL tables | `evaluation_runs` | `review_decisions`, `calibration_models` | `diagnostic_sessions`, `session_turns`, `session_snapshots` |
| Settings prefix | `RETRIEVAL_` | `INTEGRITY_` | `SESSION_` |

Rules:

1. **Additive only.** Add under your own names. Never rename or remove a label, property, table, route or
   response field that another vertical reads without a decision record signed by all three owners.
2. The label `Component` belongs to the deleted legacy domain. Do not reuse it. Maintenance parts are `Part`.
3. `Asset` and `ServiceRecord` are shared. Existing properties keep their meaning.
4. There is no migration tool for PostgreSQL. `create_all` creates new tables and never alters existing ones.
   In December, add tables. Do not change the columns of a table that already exists on staging.
5. Graph migrations live in `backend/graph/migrations/NNN_<vertical>_<what>.py`. Each is idempotent
   (`MERGE`, `IF NOT EXISTS`), has a `--dry-run` that prints counts, and is run on staging only by Umar after a backup.
6. Neo4j has no uniqueness constraints today (uniqueness is check-then-create). Do not assume one exists.

---

## 6. Evaluation discipline (applies to all three verticals)

1. **Year split.** Fit on 2023. Choose models, weights and thresholds on 2024. Report on 2025.
2. **2025 is touched once per method version.** A re-run after changing a method is logged in the results file with the reason.
   No weight, threshold or prompt is tuned on 2025.
3. **Two kinds of time.** Occurrence time is `DifficultyDate`. Knowledge time is `SubmissionDate`.
   "What was known when" always uses knowledge time.
4. **Leakage rule.** A query built from report `q` may see only reports with `submitted_at < q.submitted_at`,
   and never a report in `q`'s own citation chain. Each harness has a test that fails if this is violated.
5. **Intervals.** Every reported metric on 2025 carries a 95% bootstrap interval (1,000 resamples). The 2025 pair set has about 141 to 157 cases.
6. **Honest negatives.** If the new method does not beat the baseline, report it with the error analysis.
7. **Reproducible.** One command from a clean checkout reproduces each table. Results are committed as small JSON files with
   the commit hash, corpus fingerprint, split and seed.
8. **Scores are not probabilities** unless a calibration measurement on 2025 supports the word.

---

## 7. Language-model rules

1. The model never decides a ranking or a validity link alone. A model label is one feature. A model reply explains.
2. Classification uses the staging model (`phi4-mini` through the OpenAI-compatible path) so benchmark numbers describe staging.
3. Prompts live in `<package>/prompts.py` with a `PROMPT_VERSION` constant. A prompt change bumps the version and invalidates caches.
4. Every model output shown to a user passes the citation checks. An ID the graph does not contain is never shown as verified.
5. Halite is decision support. No output approves a repair, certifies airworthiness or replaces a licensed inspector.

---

## 8. Pull requests, tests and the knowledge bank

- Branch names: `feat/<vertical>/<topic>`, `fix/<vertical>/<topic>`, `prep/<area>`.
- Small pull requests. CI green. One reviewer from **another** vertical.
- Commit daily. The handbook names sudden code volume as a red flag.
- Every pull request description states: the work package ID, the acceptance evidence, the knowledge-bank files updated,
  and an AI-assistance note (what the agent produced, what the human checked and changed). The note feeds Form 13.
- `AGENTS.md` still applies: update `knowledge/context`, `knowledge/flows` and add a `knowledge/decisions/DEC-*.md`
  in the same change as the code.
- New graph access needs two implementations: a Cypher branch and a memory-store branch, plus a contract test.
- `tests/test_graph_maintenance.py` deletes every `ServiceRecord` and `Asset` node in its teardown (line 64).
  Never point tests at a database that holds real data.
- Staging changes only by a deploy from `main`. Nobody runs ad-hoc writes against staging.

---

## 9. Verified facts about the code at the base commit

These were read in the code on 20 November. Line numbers refer to `ac5aa66`.

| # | Fact | Where | Owner of the fix |
| --- | --- | --- | --- |
| 1 | The fleet scan never excludes the selected aircraft: it compares `asset_key` (a tail number) with `exclude_asset_id` (an Asset UUID). | `services/diagnostic_retrieval.py:118-127` | Umar |
| 2 | The aircraft-history term of the ranker is `0.4 * 1/(i+1) * penalty` and contains no symptom. | `services/diagnostic_retrieval.py:316` in `rank_diagnostic_checks` | Umar |
| 3 | The fleet scan loads the newest 2,500 reports and scores them in Python per request; the Copilot does it twice per turn. | `services/diagnostic_retrieval.py:15, 112` | Umar |
| 4 | "Superseded" is read from `status`, and `superseding_record` is read but never written. | `services/diagnostic_retrieval.py:42-43, 82, 199` | Umar, with Shahmeer's `validity.py` |
| 5 | Only the top candidate is classified, and its ID is not stored on the record. | `services/conflict_engine.py:623-624, 724-744` | Shahmeer |
| 6 | The review screen calls `GET /maintenance/records/{id}`, which re-runs the engine in dry-run mode with live model calls. | `api/routes/maintenance.py:244-267` | Shahmeer |
| 7 | The explicit-citation signal checks only that the phrase is present. The cited ID is never parsed. | `services/conflict_engine.py:457, 676` | Shahmeer |
| 8 | `recency_advantage` and `proximity_bonus` use `days_between` from `occurred_at`. It is 0 for every FAA correction, so both are false on true corrections. | `services/conflict_engine.py:439, 680, 693` | Shahmeer |
| 9 | `authority_advantage` is always true because `source_authority` returns 5 for every record. | `domains/maintenance.py:54-56` | Shahmeer |
| 10 | With facts 8 and 9, a `supersedes` label alone scores 0.35 + 0.15 = 0.50 without a citation and auto-accepts at the 0.50 threshold. | `services/conflict_engine.py:53-60, 513-526` | Shahmeer |
| 11 | Accept and reject only relabel the record. Accept creates no `SUPERSEDES` link and reject removes none. | `api/routes/maintenance.py:513-607` | Shahmeer |
| 12 | Processing a record again overwrites `status`, including `superseded`, `accepted` and `rejected`. | `services/conflict_engine.py:724-726` | Shahmeer |
| 13 | The OpenAI-compatible path forces JSON output on every call. | `services/groq_service.py:70` | Usman |
| 14 | `/maintenance/diagnose` returns 503 when no model is live, although ranking and evidence need no model. Its cache is never invalidated. | `api/routes/diagnostics.py:386-520, 93-123` | Usman |
| 15 | Diagnose citation validation checks that an ID exists in the graph, not that it was in the evidence shown. | `services/citation_validation.py:30` | Usman |
| 16 | Copilot sessions live only in `localStorage` (`halite-diagnostic-active-workspace`, `halite-diagnostic-copilot-sessions`), are not user-scoped and are not cleared at logout. | `frontend/src/utils/diagnosticWorkspace.js`, `frontend/src/context/AuthContext.jsx:62-67` | Usman |
| 17 | `PRECEDED_BY` is written at ingest and never read by any query. | `agents/maintenance_agent.py:194, 255` | Nobody; do not build on it |
| 18 | `langchain*`, `python-dotenv`, `python-docx` are in `requirements.txt` and never imported. `pypdf` and `pytest-cov` are available. | `requirements.txt` | Usman |
| 19 | Staging: 2,079 reports; after the 16 November backfill 1,585 scored, 494 needs review, 0 reviewed; methods 1,043 screen, 801 model, 235 escalated; model `phi4-mini`; the run took about 12 hours 50 minutes. | `docs/mid1/25_local_llm_staging_evidence.md` | Context |
| 20 | The published F1 of 0.762 came from `openai/gpt-oss-120b`; the harness that produced `gt_results.csv` is not in the repo; the classifier could see the phrase that defines the label. | `docs/evaluation_results.md` | Shahmeer replaces it |

---

## 10. What no agent may do

- Edit another vertical's files, or the shared registration files after the preparation window.
- Tune anything on 2025 data, or report a 2025 number without its interval.
- Invent an FAA code meaning, a statistic, a citation or a test result. If you did not run it, say so.
- Present a score as a probability, or a model sentence as verified, without the measurement that supports it.
- Write to staging, or point a test at a database with real data.
- Write the human's design note, labels or error analysis. Draft tooling for them; the judgement is theirs.
- Add a dependency without the owner's approval. Adding `torch` to the API image is not approved; use an ONNX runtime for embeddings.

---

## 11. Presentation standard

The work is graded in a 15-minute live presentation, so it must look finished and the research must be visible.

1. **Every experiment ends in a chart on a product page.** A result that exists only in a JSON file or the report is not done.
2. **No hand-typed numbers.** Every figure on screen comes from a committed results file or the live database.
3. **One look.** Use the primitives in `src/components/ui/` and the one chart library. Shahmeer owns both and provides a
   chart wrapper that fixes colours, interval whiskers and the caption. No page invents its own styling.
4. **Charts read the same way everywhere.** Each shows the sample size, the data year and 95% intervals, and uses the same
   colour for "ours" and for "baseline".
5. **Motion only where it carries meaning:** belief bars moving after an answer, a link appearing after an accept.
6. **Every page has loading, empty and error states,** and is checked in dark and light themes at 1280 pixels wide.
7. **Nothing on screen overstates.** A score is called a score. A sentence the checker did not support is shown as unsupported.
