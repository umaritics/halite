# Frontend evidence — FYP-I Mid

Owner: Shahmeer Atif (23I-0711) · Scope: `frontend/src/**` and frontend tests only
Branch: `feat/mid1/frontend-diagnostics` · Date: 2026-10-16

| Item | Value |
| --- | --- |
| Baseline SHA | `8840c68c32054bf1e9dd1505bbbdef4e22d26f6c` (`feat/maintenance-domain`) |
| Code SHA verified | `1473e778e55c3840e83bc5234416a88f439256fc` |
| Runtime used for live checks | Neo4j (docker `halite-neo4j-dev`), FastAPI on :8000, Vite on :5173 |
| `/api/health` during live checks | `graph_mode=neo4j`, `llm_mode=live` (`openai/gpt-oss-120b`), `maintenance_record_count=2079`, `using_memory_graph=false` |
| Node / npm | v26.11.1 / 11.20.0 |

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

Result on `1473e77`: **10 files, 75 tests, 75 passed, 0 failed, 0 unhandled errors**; build succeeds
(851 modules). Per file: Diagnostics 18, diagnosticsUtils 20, ReviewQueue 15, AssetHistory 9,
Assets 3, DomainContext 3, Sidebar 3, ServiceRecords 2, MaintenanceIngest 1, dummy 1.

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

- **No hosted CI run for this branch.** The only workflow (`.github/workflows/ci.yml`) is on `origin/usman`,
  not on this branch. Local results are not CI results. CI uses Node 20; these runs used Node 26.
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

For **Usman** (maintenance routes, tests, deployment):
- `GET /maintenance/records/{id}` re-runs the conflict engine (an LLM call) on every view.
- `GET /maintenance/assets/{id}/history` is keyed by UUID; a tail number returns 404. Record this in the contract.
- `backend/tests/test_graph_maintenance.py` has a `neo4j` fixture that defaults to `bolt://localhost:7687` and, on
  teardown, deletes every `ServiceRecord` and `Asset`. Running the full suite while the dev Neo4j is up wipes the corpus.
- `DELETE /api/graph/reset` wipes the whole graph and is reachable by anyone calling the API.
- Hosted CI for the frontend job: the `ReviewQueue` test failure in `06_frontend_review_queue_handoff.md`
  (on `usman`) is fixed in `6e36897` and the full local suite is 75/75; a hosted re-run is still required.
- Vercel previews are behind SSO; the canonical project and reviewer access are still to be sorted out.

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
