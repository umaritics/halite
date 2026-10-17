# Frontend evidence — FYP-I Mid

Owner: Shahmeer Atif (23I-0711) · Scope: `frontend/src/**` and frontend tests only
Branch: `feat/mid1/frontend-diagnostics` · Date: 2026-10-16

| Item | Value |
| --- | --- |
| Baseline SHA | `8840c68c32054bf1e9dd1505bbbdef4e22d26f6c` (`feat/maintenance-domain`); `origin/main` `b85dde0` merged in at `9fdc780` |
| Code SHA verified | `8c59079df56b34588122d66d7890a38a54219025` (docs/knowledge-only commits follow; no code changes) |
| Runtime used for live checks | Neo4j (docker `halite-neo4j-dev`), FastAPI on :8000, Vite on :5173 |
| `/api/health` during live checks | `graph_mode=neo4j`, `llm_mode=live` (`openai/gpt-oss-120b`), `maintenance_record_count=2079`, `using_memory_graph=false` |
| Node / npm | v26.11.1 / 11.20.0 |

> **Addendum, 2026-10-18:** this document is a snapshot of 16 Oct. Work merged after it (PRs #5–#12) is recorded in [§13](#13-addendum-2026-10-18-work-merged-after-this-snapshot);
> where §3 and §12 say "unchanged", "unmerged" or "not yet on `main`", §13 is current.

Everything below was executed on the SHA above. Where something was **not** verified, it says so
(see [Limitations](#7-limitations-and-what-was-not-verified)).

## 1. Commits (frontend lane only)

| SHA | Work package | Summary |
| --- | --- | --- |
| `6e36897` | S5 | Fix `ReviewQueue` test mock (`getRecord`); in-memory `localStorage` in test setup (Node ≥ 25) |
| `4919461` | S1 | Maintenance-only navigation, landing, settings, routes, domain lock |
| `934b9da` | S3 | Diagnostics states, warnings, safer rendering |
| `97833c6` | S4 (+S2 states) | Record deep links, review-queue safety, history error states |
| `1473e77` | S4 | Instant jump to cited record; scrollable review finding panel |
| `9fdc780` | merge | `origin/main` merged into this branch (clean, no conflicts) |
| `d69039d` | handoff 10 | Service Records loads one aircraft at a time |
| `2b66978` | handoff 12 | Diagnose UI follows the frozen contract; notice when the model returns nothing |
| `8c59079` | handoff 14 | `npm audit fix` (axios, react-router patch) |

A separate, unmerged branch `feat/mid1/graph-webgl-fallback` (`6678736`) holds one extra fix (WebGL check and
error boundary for the 3D graph). It is not part of the SHA verified here.

## 2. Work package status

| Package | Result | Evidence |
| --- | --- | --- |
| S1 Navigation / legacy isolation | Done | `logs/route-smoke.txt`, screenshots 01, 02, 05; tests `Sidebar` (3), `DomainContext` (3) |
| S2 Asset list and history | Done | screenshots 02–04, 13; tests `Assets` (3), `AssetHistory` (9) |
| S3 Diagnostic workspace | Done | screenshots 06, 07, 10, 12; tests `Diagnostics` (18), `diagnosticsUtils` (20) |
| S4 Evidence navigation and review UI | Done | screenshots 03, 08, 09, 11, 13; tests `ReviewQueue` (15) |
| S5 Quality and tests | Done for tests/build; no linter exists (see §7) | `logs/frontend-tests.txt`, `logs/frontend-build.txt` |

## 3. Routes

| Route | Page | Notes |
| --- | --- | --- |
| `/` | Landing | Maintenance copy; buttons open `/app/assets` and `/app/diagnostics` |
| `/app` | → `/app/assets` | Redirect |
| `/app/assets` | Assets | List from `GET /api/maintenance/assets` |
| `/app/asset-history/:assetId[#recordId]` | AssetHistory | `:assetId` must be the asset **UUID**; `#recordId` scrolls to and marks the record |
| `/app/records` | Service Records | Search/filter over records |
| `/app/diagnostics` | Diagnostics | `POST /api/maintenance/diagnose` |
| `/app/review-queue` | Review Queue | Conflict review |
| `/app/maintenance-ingest` | Maintenance Ingest | Existing ingest page (unchanged) |
| `/app/graph` | Knowledge Graph | Existing 3D graph (unchanged apart from the hidden chat button) |
| `/app/settings` | Settings | Theme + System Status (health) only |
| `/app/chat`, `/decisions`, `/ingest`, `/alerts`, unknown | → `/app/assets` | Legacy software URLs redirect; files remain in the repo |

## 4. API integration notes

| Page | Endpoints used | Response fields the UI reads |
| --- | --- | --- |
| Assets | `GET /maintenance/assets` | `id` (UUID), `tail_number`, `make`, `model`, `serial_number`, `record_count` |
| AssetHistory | `GET /maintenance/assets/{uuid}/history` | `records[]`: `record_id`, `occurred_at`, `status`, `part_name`, `part_condition`, `part_location`, `text`, `asset_key`; optional `superseding_record`, `supersede_rationale` |
| Diagnostics | `GET /maintenance/assets`, `POST /maintenance/diagnose` | `ranked_checks[]` (`part_name`, `evidence_count`, `sources`), `evidence[]`, `rare_cases[]`, `explanation`, `context_size`, `citation_validation`, `warnings` |
| ReviewQueue | `GET /maintenance/review-queue`, `GET /maintenance/records/{id}`, `GET /maintenance/assets`, `POST …/review-queue/{id}/accept`, `POST …/reject` | Queue row: `record_id`, `asset_key`, `classification_label`, `classification_rationale`, `confidence`, `candidates_considered`, `history_size`. Detail: `best_prior`, `classification`, `confidence`, `candidates_considered` |
| Settings | `GET /health` | `graph_mode`, `llm_mode`, `model`, `maintenance_record_count`, `maint_threshold` |

All optional fields are treated as optional. Fixtures captured from the live backend are in `fixtures/`.

### Error handling the UI implements (Diagnostics)

| HTTP / condition | UI | Verified |
| --- | --- | --- |
| 200, evidence present | Ranking, analysis, citation status, evidence, warnings | live (06, 07) |
| 200, no evidence | "Insufficient evidence"; ranking and narrative withheld | unit test only |
| 404 | "No service history for this aircraft" (no retry) | unit test; history page 404 live (04) |
| 422 | "Check the request" with flattened field messages | unit test; real shape in `fixtures/error_422_validation.json` |
| 429 | "Model rate limit reached" + retry | unit test only |
| 503 | "Diagnostic model unavailable" + backend detail + retry | **live, real** (10), plus fixture |
| 5xx | "The diagnostic service hit an error (HTTP n)" + retry | **live** (12: backend stopped → dev proxy returns 500); recovery after restart confirmed |
| Network error | "Cannot reach the Halite API" + retry | unit test only |

## 5. Test evidence

Commands (from `frontend/`):

```bash
npm test -- --run --reporter=verbose   # logs/frontend-tests.txt
npm run build                          # logs/frontend-build.txt
```

Result on `8c59079`: **10 files, 99 tests, 99 passed, 0 failed, 0 unhandled errors**; build succeeds.
Per file: Diagnostics 25, diagnosticsUtils 24, ServiceRecords 15, ReviewQueue 15, AssetHistory 9,
Assets 3, DomainContext 3, Sidebar 3, MaintenanceIngest 1, dummy 1. (At `1473e77` the suite was 75 tests; the
Service Records, contract and notice work added 24.) `origin/main` still shows 12 passed / 1 failed because the
`ReviewQueue` mock fix is only on this branch.

Before this work the suite had 13 tests; Usman's hosted run recorded 12 passing and 1 failing
(`ReviewQueue`), and on Node 26 a second test (`DomainContext`) also failed locally.

**What these tests are.** They are component tests with the API client mocked. They prove the UI
behaves correctly for each response shape. They do **not** by themselves prove the live integration;
that was checked by hand against the running stack (§6).

**Mutation checks.** To confirm the new tests can fail, the code was deliberately broken and the
tests re-run. Each break was caught by the intended test, then the file was restored:

| Deliberate break | Caught by |
| --- | --- |
| Disable the insufficient-evidence state | Diagnostics: "200 with no evidence…" |
| Remove the duplicate-submit guard | Diagnostics: "blocks duplicate submissions" |
| Render the raw model JSON explanation | Diagnostics: "shows readable text when the backend returns raw model JSON" |
| Remove handler guard + disabled buttons while accept is pending | ReviewQueue: "does not remove the record… until the server confirms" |
| Keep the previous finding on screen while the next loads | ReviewQueue: "never shows the previous record's finding…" |
| Swallow a queue fetch error | ReviewQueue: "a failed fetch is reported as a failure…" |
| Re-add the bare `A` accept shortcut | ReviewQueue: "a stray key press cannot accept or reject" |

The tests also caught one real defect: the deep-link scroll ran while the loading skeleton was still
on screen and never re-ran.

## 6. Live verification (executed, with screenshots)

Screenshots are in `screenshots/` (captured in the Claude desktop Browser pane at 1280×800, downscaled to
800 px wide by the capture tool). No credentials appear in any capture.

| # | File | Shows | Blueprint |
| --- | --- | --- | --- |
| 01 | `01_landing_maintenance.jpg` | Maintenance landing page | T01, T16 |
| 02 | `02_assets_live_corpus.jpg` | 118-asset list; Review Queue badge = 9 (real count) | T01, T02 |
| 03 | `03_history_linked_record.jpg` | Citation deep link: record centred and marked "Linked record" in a 153-record history | T03 |
| 04 | `04_history_unknown_asset_404.jpg` | Unknown asset → "Aircraft not found" (not "no records") | T06 (UI) |
| 05 | `05_settings_system_status.jpg` | `neo4j`, `live`, model, 2079 records | T14 (display) |
| 06 | `06_diagnostics_ranked_checks.jpg` | 813SK + "crack found on drag angle during inspection": ranked checks | T04 |
| 07 | `07_diagnostics_analysis_citations_evidence.jpg` | Analysis, "12 cited record IDs verified", evidence records | T05 |
| 08 | `08_review_queue_incoming_and_prior.jpg` | Live review case 163AA: incoming vs retrieved prior record | T09 |
| 09 | `09_review_queue_rationale_and_actions.jpg` | Label meaning, rationale, "Examined 9 of 15", Accept/Reject with the "neither deletes the record" note | T09 |
| 10 | `10_diagnostics_model_unavailable_real_503.jpg` | **Real 503**: backend started with `GROQ_API_KEY` empty; no diagnosis shown | T07 |
| 11 | `11_review_queue_model_unavailable_stored_finding.jpg` | Same condition on the review queue: failure explained, stored finding shown and labelled | T07 |
| 12 | `12_diagnostics_backend_down_http_500.jpg` | Backend stopped: HTTP 500 reported with retry; retry recovered once the backend returned | T07 |
| 13 | `13_history_superseded_no_invented_text.jpg` | Real superseded record shows only "Superseded by a later record." | Adversarial case 2 |

Other live checks (no screenshot): deep link to a record from the review queue lands on the right
aircraft and marks the record; `logs/route-smoke.txt` covers all 14 route cases.

### How the real failure states were produced

- **Model unavailable (10, 11):** the backend was stopped and restarted with `GROQ_API_KEY=` (empty) on
  port 8000, Neo4j unchanged. `/api/health` then reported `llm_mode=fallback`, `groq_configured=false`,
  and `POST /diagnose` for an uncached symptom returned a real 503. The normal backend was restored afterwards
  (`neo4j / live / 2079` confirmed).
- **Backend down (12):** the page was loaded and an aircraft and symptom entered while the backend was up;
  the backend was then stopped and the form submitted. In development the Vite proxy answers 500 when
  the backend is unreachable, so the UI shows the 5xx state, not the "cannot reach API" state.

## 7. Limitations and what was not verified

- **No hosted CI run for this branch yet.** `main` has the workflow and its last run showed backend and Docker jobs
  green and the frontend job red (the mock fixed here). This branch has not been pushed, so there is no hosted result for
  it. Local results are not CI results. CI uses Node 20; these runs used Node 26.
- **Staging screenshots were not captured.** The Browser pane was only ~359 px wide during the staging pass, so the
  staging evidence is numeric (`logs/staging-measurements.txt`). Screenshots 01–13 are from the local stack.
- **No static analysis beyond the build.** The frontend has no lint script and ESLint is not installed.
  "Static check" here means only that `vite build` compiles.
- **Accept / Reject were not exercised against real data.** They change a record's status in Neo4j and
  cannot be undone from the UI. They are covered by mocked tests only (§5). Do not click them on the demo corpus.
- **Insufficient-evidence, 429 and network-error states** are unit-tested only; they were not reproduced live.
- **One non-fatal React console warning** ("uncontrolled input to controlled") appeared once during the first
  combined route pass and did not reproduce per route; its source was not identified.
- **Not tested:** phone/tablet widths, browsers other than the embedded pane, light theme for the new states,
  keyboard-only navigation, accessibility tooling.
- **Diagnostic quality is not evaluated here.** The ranking is a frequency/lift-based score (per `docs/maintenance_handoff.md`), not a calibrated
  probability; the UI says so. The citation check confirms record IDs exist, not that each statement is supported.
- **Legacy software pages still exist in the repo.** They are unreachable from the UI (routes redirect), not deleted.
- **Backend `DELETE /api/graph/reset` is still exposed.** The UI button was removed, but the endpoint remains.

## 8. Behaviour changes the team should know about

1. The Settings page no longer has "Reset knowledge graph" (it ran `MATCH (n) DETACH DELETE n`) or
   "Agent context export".
2. Review queue: the bare `A` / `R` keyboard shortcuts for accept/reject were removed (arrow-key navigation stays).
   Accept/Reject now wait for the server before updating the screen.
3. The Review Queue badge now shows the real review-queue count (it used the software alerts count).
4. Asset history no longer prints "Superseded by Unknown — Previous record invalidated"; it shows only
   backend-supplied values.

## 9. Requests to other owners (for written issues)

For **Umar** (diagnostics route):
- A Groq failure raises `RuntimeError` and surfaces as a bare HTTP 500. The blueprint expects 503/429.
- When the model's JSON cannot be parsed (`diagnostics.py`, around line 304) the raw text is returned as
  `explanation`. The UI now recovers the text, but the backend should parse it properly.
- With the model unavailable, an unknown asset returns 503 (the model check runs before the history check).
  It returns 404 only when the model is live.
- **On shared staging, fresh diagnose calls return an empty `explanation`, empty `evidence` and empty citation lists**
  (3 of 3 symptoms; ranking present; `llm_mode=live`). The same merged code run locally returned a full explanation
  for 1 of 2 symptoms (the other returned 18 characters). Cause not established from outside; needs staging logs.
  See `logs/staging-measurements.txt`. If the demo runs on staging this removes the Analysis, citations and evidence cards.
  **New lead (2026-10-16, via the Settings page after the next merge):** staging's pinned model is `openai/gpt-oss-20b`; the local stack uses
  `openai/gpt-oss-120b`. A smaller reasoning model with the route's small token limit is a plausible cause of empty text; unconfirmed.

For **Usman** (maintenance routes, tests, deployment):
- `GET /maintenance/records/{id}` re-runs the conflict engine (an LLM call) on every view.
- **Shared staging has no conflict-engine output (checked 2026-10-16):** `GET /maintenance/review-queue` returns 0 items, all 153 of 813SK's records
  are `auto_accepted` (locally: 9 queue items, 1 superseded record), and a 2000-node graph sample contains no `SUPERSEDES` edges. The review UI is linked and
  tested, but there is nothing to show on staging until the conflict backfill is run there.
- The history API exposes no field naming the superseding record, so the UI can say a record was superseded but not by which one.
- `GET /maintenance/assets/{id}/history` is keyed by UUID; a tail number returns 404. Record this in the contract.
- `backend/tests/test_graph_maintenance.py` has a `neo4j` fixture that defaults to `bolt://localhost:7687` and, on
  teardown, deletes every `ServiceRecord` and `Asset`. Running the full suite while the dev Neo4j is up wipes the corpus.
- `DELETE /api/graph/reset` wipes the whole graph and is reachable by anyone calling the API.
- Hosted CI for the frontend job: the `ReviewQueue` test failure in `06_frontend_review_queue_handoff.md`
  (on `usman`) is fixed in `6e36897` and the full local suite is now 99/99; a hosted re-run is still required.
- Vercel previews are behind SSO; the canonical project and reviewer access are still to be sorted out.
- Still present on `origin/main` (checked 2026-10-16): the `DELETE /api/graph/reset` route (`backend/api/routes/graph.py`) and the
  `neo4j` fixture in `test_graph_maintenance.py` that deletes every `ServiceRecord`/`Asset` on teardown.

## 10. Reproduce

```bash
docker compose up -d neo4j
cd backend && python3.10 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env     # set DEMO_MODE=false, NEO4J_URI=bolt://localhost:7687, GROQ_API_KEY=<your key>
python scripts/fetch_sdr_data.py && uvicorn main:app --port 8000
# new terminal
cd frontend && npm ci && npm test -- --run && npm run build && npm run dev
```

Do **not** run the full backend `pytest` while Neo4j is running (see §9). Use
`python -m pytest -q --ignore=tests/test_graph_maintenance.py`.

## 11. AI assistance (draft disclosure — Shahmeer to review and own)

The frontend changes in this document were produced with an AI coding agent (Claude Code, model
Claude Sonnet 5.5) working under Shahmeer's direction. Each change was verified by executing the tests,
build and live checks listed above; none is claimed from generated code alone. The external model used
inside the product is Groq `openai/gpt-oss-120b`, called from the backend for diagnostic phrasing and conflict
classification. Shahmeer remains responsible for being able to explain every change above.

## 12. Response to the Mid-I handoffs on `main` (docs 10, 12, 14)

| Item | Source | Status | Evidence |
| --- | --- | --- | --- |
| Stop the all-aircraft history fan-out; initial load ≤ 2 calls | 10, 14 | **Done** on this branch | Production build vs staging: 2 page-initiated calls on first load (assets 688 ms + one history 1221 ms) plus the app shell's `review-queue` badge call = 3 in the network tab; switching aircraft adds 1 call (926 ms). Before: 1 + 118. `logs/staging-measurements.txt`; `ServiceRecords.test.jsx` enforces the 118-aircraft request count |
| Diagnostics dropdown usable without a long wait | 10 | **Done** (backend fix) | Staging assets call 0.99 s (curl) / 923 ms (browser). The page still makes a single assets call |
| Fix the `ReviewQueue` test mock; frontend CI job | 06, 14 | **Fixed here, not yet on `main`** | `6e36897`; 99/99 locally; hosted run still needed |
| Re-run tests and build; provide the branch | 14 | Tests/build done; **branch not pushed** | `logs/frontend-tests.txt`, `logs/frontend-build.txt` |
| Dependency advisories (axios, react-router) | 14 | **Partly done** | `npm audit --omit=dev`: 3 → 2 advisories. axios 1.18.1 → 1.20.0 (high cleared); react-router(-dom) 6.30.4 → 6.30.6. **Two moderate react-router 6.x advisories remain**; the only fix is react-router 7 (breaking), deferred because this is a client-only SPA with fixed `/app/...` link prefixes and the change is risky this close to evaluation. Not changed: dev-only vitest advisories (breaking fix). `logs/npm-audit-prod.txt` |
| Diagnose UI checklist (`evidence_record_ids` click-through, `all_valid` gate, `[UNVERIFIED]` styling, 503/404 copy, long-request loading) | 12 | **Done** | Tests in `Diagnostics.test.jsx`, `diagnosticsUtils.test.js`. Per-check record ids link only when the record is in the response's `evidence` array (its aircraft is known); other ids stay plain text |
| Add personally used AI tools to the report disclosure | 14, 15 | **Open** | Draft wording in §11; `docs/mid1/15_report_mid1_addendum.md` currently lists only OpenAI Codex and its PDF must be regenerated (`scripts/render_mid1_addendum.py`) |
| Supervisor sign-off | 14 | **Open** (Shahmeer) | — |

Notes:
- `frontend/.env.development` now points `npm run dev` at shared staging. Use a local `.env.local` for a local backend.
  `.env.local` is **not** in `.gitignore` as of this check even though other docs say it is; do not commit it.
- Asset UUIDs differ between local Neo4j and staging (813SK: `aa4e5d11-…` vs `92bdb741-…`). Deep links with a UUID are environment-specific.
- Staging is shared: Accept/Reject there would change the corpus everyone, including the demo, uses.
- Dev builds run React in StrictMode, which doubles effect-driven requests; request counts above are from a production build.

## 13. Addendum (2026-10-18): work merged after this snapshot

Verified on `main` at `5bf5961` (merge of PR #12): `npm test -- --run` **171 passed (15 files)**, `npm run build` passes, hosted CI
(backend tests, frontend tests and build, real-Neo4j Docker smoke) **success** on that SHA.

### 13.1 Frontend PRs

| PR | Merge SHA | Change |
| --- | --- | --- |
| #9 | `77fe7d6` | Knowledge Graph shows one aircraft's stored subgraph (backend limit 3000; opens on the busiest aircraft; truthful node/edge counts; `SUPERSEDES` drawn apart from `ABOUT`/`PRECEDED_BY` with a legend; tail/record-ID labels; stored-field side panel; legacy software nodes removed). Staging check: 813SK = 154 nodes / 305 edges. [DEC-20261017-graph-aircraft-focus](../../knowledge/decisions/DEC-20261017-graph-aircraft-focus.md) |
| #10 | `e6abdc9` | Ingest page: CSV upload via the existing `POST /maintenance/ingest/upload` (explicit confirm step, `.csv` ≤ 10 MB), backend counts relabelled for what they count, inline errors instead of `alert()`, `MM/DD/YYYY` stated. [DEC-20261017-ingest-csv-upload-ui](../../knowledge/decisions/DEC-20261017-ingest-csv-upload-ui.md) |
| #11 | `a5d1399` | Graph spacing: link distance, charge and node size so small graphs do not hide their edges; layout warm-up |
| #8, #12 | `062f9a1`, `5bf5961` | Docs and evidence (this document's siblings: [23_single_aircraft_analysis_evidence.md](23_single_aircraft_analysis_evidence.md)) |

PRs #5–#7 (diagnostic copilot, confidence and corrections, analysis cost cascade) were authored by Usman and merged earlier; the frontend consumes them in Service Records, the Review Queue
(Detected corrections tab) and Diagnostics. Service Records is now fleet-wide and paginated. §3's "unchanged" notes for the Graph and Ingest pages no longer apply.

### 13.2 New screenshots (scratch graph, aircraft 800NN)

Captured 2026-10-18 in the Claude desktop Browser pane (1280×800 emulation, downscaled), against a **local backend on a throwaway Neo4j** that holds only the 13 `800NN` records,
analysed in `legacy` mode with `openai/gpt-oss-120b`. They are not staging. Method and results: doc 23.

| File | Shows |
| --- | --- |
| `14_records_scored_800NN.jpg` | Service Records with score, label and status per record; "heuristic, not a probability"; "No conflict found (N comparisons)" |
| `15_history_correction_800NN.jpg` | Asset History: DOOR TRACK greyed and "Corrected by AALA202506090459 — component changed DOOR TRACK → DOOR" |
| `16_review_queue_800NN.jpg` | Review Queue (2): incoming record, retrieved prior record, model rationale, Accept/Reject (not clicked) |
| `17_corrections_tab_800NN.jpg` | Detected corrections: 4 found, 3 with a component change |
| `18_graph_800NN_amber_corrections.jpg` | Knowledge Graph for 800NN: 14 nodes, 29 edges; four `SUPERSEDES` edges thick and amber; superseded record grey |
| `19_ingest_upload_nothing_new.jpg` | Ingest → Upload CSV re-upload of two already-loaded rows: 0 new, 2 already in graph |

### 13.3 Still open or not verified

- **Staging has almost no analysis output.** Checked 2026-10-18: 2,079 records, all unscored, about 16 stored findings (7 `SUPERSEDES`). Single-aircraft analysis was run on a scratch graph only; the full-corpus run was deliberately not done for Mid-I.
- **Graph side-panel click** (record or aircraft details, link to Asset History) is covered by unit tests but was **not verified live**: canvas clicks did not register in the browser tool.
- **Graph camera:** in the test browser pane the camera sometimes stayed zoomed into the hub until the page was redrawn; time-to-fit on a real GPU was not measured.
- **WebGL fallback:** the WebGL check and error boundary (originally `6678736`, never merged) was re-applied in the follow-up PR to the Graph page. Verified live in the browser pane with WebGL removed (message shown, no canvas, legend and navigation still work) and by two unit tests; a real browser with hardware acceleration switched off was not tried.
- **Ingest** was exercised on a local in-memory backend and a scratch Neo4j only, not on staging and not with a full-size file. The backend answers an unreadable CSV (for example an empty file) with an unhandled HTTP 500 without CORS headers, which browsers report as a network failure (owner: Usman).
- **Cosmetic:** on narrow layouts the long `partial_supersedes` label runs into its score in `ConfidenceBar`.
- **§12 items now closed:** the `ReviewQueue` test fix, the fan-out fix and the dependency patches are on `main`, with hosted CI green. **Still open:** react-router 7 upgrade (deferred), the report's tool disclosure (Form 13 and addendum), supervisor sign-off.
- The staging explanation gap in §9 (empty `explanation` on staging, model `openai/gpt-oss-20b`) has not been re-checked since 2026-10-16.

