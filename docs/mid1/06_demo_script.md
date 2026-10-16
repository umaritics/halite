# Mid-I demo script and defence notes

Owner of this file: Shahmeer Atif. Steps 1, 3 and 5 are Shahmeer's; steps 2, 4, 6, 8 belong to Usman and Umar
(blueprint §12.1) and are included only so the hand-offs line up. Total target 8–12 minutes.

Record IDs (SWIA…, AALA…) are the same everywhere. **Asset UUIDs are not**: 813SK is `92bdb741-42cb-4ccb-a65f-6ed5fbb7d1a4` on the
local Neo4j used for the screenshots and `aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb` on shared staging (2026-10-16). To avoid
typing a UUID, open Assets → 813SK and use the links the app gives you.

## Choose the backend first

`frontend/.env.development` (merged from `main`) points `npm run dev` at **shared staging**. Pick one and say which you used.

| | Local stack | Shared staging |
| --- | --- | --- |
| Setup | Docker Neo4j + local backend; create git-ignored `frontend/.env.local` with `VITE_API_URL=/api` and `VITE_PROXY_TARGET=http://localhost:8000` | nothing; `npm run dev` |
| Diagnosis narrative | Worked in my checks (full explanation, 10 evidence records, 13 verified citations for the drag-angle case) | **Returned no explanation on 2026-10-16** (3 of 3 fresh symptoms): ranking only, no Analysis / citations / evidence cards. Confirm with Umar/Usman that this is fixed **before** demoing step 5 on staging |
| Risk | Your machine only | Shared corpus: Accept/Reject would change data for everyone |

**Check `/api/health` agrees before you claim anything:** `graph_mode=neo4j`, `llm_mode=live`, `maintenance_corpus_loaded=true`.

## Before you start (5 minutes, not on stage)

```bash
docker compose up -d neo4j                                                   # local mode only
cd backend && source venv/bin/activate && uvicorn main:app --port 8000     # local mode only, terminal 1
cd frontend && npm run dev                                                   # terminal 2
curl -s localhost:8000/api/health   # local; or https://dev1.corp.curatech.pk/halite-api/api/health for staging
```

1. Open `http://localhost:5173/`. Check the sidebar shows only: Assets, Service Records, Diagnostics, Review Queue, Ingest,
   Knowledge Graph, Settings.
2. **Warm the cache:** run aircraft **813SK** with symptom **`crack found on drag angle during inspection`** once.
   A cached answer skips the model call; an uncached one calls Groq and is slower (the maintenance handoff puts warm queries at about 2–3 seconds).
   Check the result actually has an **Analysis** section; if it shows "No written explanation returned", the model returned nothing.
3. Open the Review Queue once and wait for the finding to load (it also calls the model).
4. Have these tabs ready (use the UUID for your environment; see above):
   - Linked-record view: `/app/asset-history/<813SK uuid>#SWIA2025122076513`
   - Failure view: `/app/asset-history/ZZ999`
5. Backup: `docs/mid1/screenshots/` (13 stills, captured on the local stack) and `docs/mid1/fixtures/`.

**Never click Accept or Reject on the real queue.** They permanently change a record's status in the corpus and
cannot be undone from the UI. Talk through the screen instead.

## Step 1 — Shahmeer: introduce Halite and the real data (about 1 min)

Say: "Halite is decision support for maintenance. It links historical service reports into a graph, ranks what to
investigate, and ties every suggestion back to a source record. It does not approve repairs."

Do: landing page → **Open the Workspace** → **Assets**.
Point out: 118 aircraft, each with a real record count (813SK has 153); Review Queue badge shows the real queue size (9).

If it fails: assets don't load → check `curl localhost:8000/api/health`; show `screenshots/02_assets_live_corpus.jpg`.

## Step 2 — Usman: runtime health (about 1 min)

Open **Settings → System Status**: `neo4j`, `live`, `openai/gpt-oss-120b`, `2079 ingested`.
(Owner: Usman. Screenshot `05_settings_system_status.jpg`.)

## Step 3 — Shahmeer: an asset's dated history (about 1 min)

Do: Assets → **813SK** (or open the Linked-record view tab). Optional, 20 seconds: **Service Records** opens one aircraft at a time (813SK by default); change the aircraft in the selector and only that aircraft's records load.
Say: "These are real FAA Service Difficulty Reports, oldest first, each with its original report ID. Nothing here is generated."
Point out: record ID at the bottom of each card; the one **superseded** record (`SWIA2025111576508`, 11/15/2025) says only
"Superseded by a later record." The API doesn't supply more, so the UI doesn't invent more.

If it fails: history blank → check `/api/maintenance/assets/<uuid>/history` returns 200 (the endpoint takes the asset UUID, not the tail number).

## Step 4 — Umar: how retrieval and ranking work (about 1 min)

(Owner: Umar.) Graph-constrained retrieval from the asset's own history plus fleet matches; a lift-based ranking over historical
symptom-to-component frequencies (see `docs/maintenance_handoff.md`); the model only phrases the answer. Not a trained predictive model.
Umar should confirm the exact scoring factors before the demo.

## Step 5 — Shahmeer: live diagnosis with cited evidence (about 2 min)

Do: **Diagnostics** → aircraft **813SK** → symptom **`crack found on drag angle during inspection`** → **Run diagnostic**.

Show, in order:
1. The line under the form: *"Diagnosis for 813SK — …"* and *"Answered from 30 records on this asset and 20 fleet-wide matches across 9 assets."*
2. **Ranked Inspection Order:** `DRAG ANGLE` first (seen in 3 prior cases; sources `asset_history, fleet_match`), then `ANGLE`, `STRINGER SPLICE`, …
3. **Analysis**, then the line *"12 cited record IDs verified against the graph. This confirms the records exist, not that every statement is supported."*
4. **Evidence Records:** click one (e.g. `SWIA2025122076513`). The history page opens **on that record**, marked "Linked record".
5. The footer: *Decision support only… not a calibrated probability…*

Say about the ranking: "The score reflects how often components appear in matching historical records. It is not a probability."

If it fails:
- Spinner never ends or a red box appears → read it aloud; it says what failed (see "Failure cases" below). Don't improvise a diagnosis.
- Use `screenshots/06_…` and `07_…` as the backup.

## Step 6 — Usman: a real conflict / review case (about 1 min)

Open **Review Queue** (wait for the finding to load). First case:

| | |
| --- | --- |
| Incoming | `AALA202510203314` (163AA, 10/12/2025): door damper and cylinder pressure low, aircraft in base maintenance |
| Retrieved prior | `AALA202507180950` (7/16/2025): "AIRCRAFT WAS NOT GROUNDED…" |
| Label | **contradicts** — "The records make mutually exclusive claims about the same part or event." |
| Confidence | 0.40, "Examined 9 of 15 records on this asset." |

Say: this is a **flag for a human**, not an adjudicated fact. Neither Accept nor Reject deletes the record. Both are
status changes; **do not click them**.

The prior record's **Open in asset history →** link opens that aircraft's history on the prior record.

## Step 7 — All: failure cases (about 1 min)

Pick one or two; each is real.

| Case | How | What the audience should see |
| --- | --- | --- |
| Unknown asset | Open `/app/asset-history/ZZ999` | "Aircraft not found" — not "no records", nothing invented (`04_…`) |
| Superseded record | History for 813SK, record `SWIA2025111576508` | Status shown; no made-up reason (`13_…`) |
| Model unavailable | Stop the backend; restart with the key blank: `cd backend && GROQ_API_KEY= venv/bin/python -m uvicorn main:app --port 8000`; run an **uncached** symptom (e.g. `intermittent chime from forward galley panel during taxi`) | "Diagnostic model unavailable… no diagnosis is shown", with the backend's reason and Try again (`10_…`). Review Queue stays usable and labels its finding as stored (`11_…`) |
| Backend down | Stop the backend after loading the page, then submit | HTTP 500 reported with Try again; after restart, Try again recovers (`12_…`) |

Restore the normal backend afterwards and re-check `/api/health`. A cached symptom still returns an answer when the model
is down; use an uncached one to show the failure.

## Step 8 — Usman: GitHub Actions evidence (about 1 min)

(Owner: Usman.) Hosted CI exists only on the `usman` branch until it is merged; show the green run URL from
`docs/mid1/07_usman_release_readiness.md` only if it is actually green on the final SHA.

## Step 9 — All: contribution split and remaining work

Shahmeer: frontend and report. Umar: graph, retrieval, ranking. Usman: data, conflict engine, CI/CD.
Remaining (from the timeline): sessions and multi-turn diagnosis, hybrid retrieval, RBAC/multi-tenancy, ingestion UI hardening,
evaluation suite, analytics, training. Not built yet: login/organisations, session persistence, vector retrieval.

## Likely questions for Shahmeer, with accurate answers

**How do the Assets and Diagnostics pages get real data?**
Axios client (`frontend/src/api/client.js`) calls `/api/maintenance/assets` and `/api/maintenance/diagnose`; Vite proxies `/api` to FastAPI,
which reads Neo4j. The page never contains sample data.

**What is the API contract and how are 404/503/empty handled?**
Diagnose takes `{asset_id (UUID), symptom_text}` and returns `ranked_checks, evidence, rare_cases, explanation, context_size,
citation_validation, warnings`. 404 → no history; 422 → validation message; 503 → model unavailable with the backend's reason and no
diagnosis; 429/5xx → retry message; 200 with no evidence → "Insufficient evidence" and the ranking is withheld. Table in `02_frontend_evidence.md` §4.

**How does a user open and verify a citation?**
Each evidence record ID is a link to `/app/asset-history/<asset uuid>#<record id>`; the page scrolls to the record and marks it. The backend validator checks that each
cited ID exists in the graph; unmatched IDs are flagged `[UNVERIFIED]`. It confirms existence, not that the sentence is supported by the record.

**How were the legacy software screens isolated without breaking the app?**
The domain is fixed to maintenance (`DomainContext`), the sidebar lists only maintenance destinations, and `/app/chat|decisions|ingest|alerts` redirect to Assets.
The files still exist in the repo. Route smoke test: `logs/route-smoke.txt`.

**How do the frontend tests verify live API behaviour?**
They don't, on their own: they are component tests with the API mocked (75 tests, every response shape and error state). The live integration was verified by hand
against the running stack with screenshots and fixtures (§6 of the evidence file). Hosted CI for this branch has not been run yet.

**Why is `ANGLE` ranked second for a drag-angle crack?**
The ranking is a frequency/lift-based score over historical records, not a trained model. `ANGLE` is supported by 17 fleet-wide cases, which is why it ranks
highly even though `DRAG ANGLE` is the more specific match. It illustrates the limit of the method. The score is not a calibrated probability.
Umar owns the exact scoring factors and should answer any follow-up.

**Did the review queue ever make a change by itself?**
No. Accept/Reject are explicit button actions and the screen only changes after the server confirms. A stray key press cannot trigger either (that shortcut was removed).

**What did the AI assistant do?**
Frontend code and tests were written with an AI coding agent under the team's direction and verified by running tests and live checks (disclosure in `02_frontend_evidence.md` §11).
The product's own model is Groq `openai/gpt-oss-120b`.

## Claims to avoid

- Don't say the system is "accurate" or "validated" for diagnosis. The measured numbers (precision 0.903 / recall 0.660) are for **conflict detection**, not diagnosis, and
  precision 0.903 leaves out wrongly linked pairs (see `docs/evaluation_results.md`).
- Don't say the first report "was wrong". Say the follow-up names a different part.
- Don't call the ranking a probability, or the citation check a proof that statements are supported.
- Don't claim CI is green until you have the hosted run for the final SHA.
