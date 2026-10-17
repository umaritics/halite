---
id: mod-frontend
title: Frontend maintenance UX
status: active
owners: [Shahmeer]
updated: 2026-10-17
---

# Module: Frontend (maintenance)

## Purpose

Maintenance-only technician UX: assets, dated history, diagnostics, review queue, ingest, graph, settings.
The software-domain screens still exist in the repo but are **not reachable** (see
[DEC-20261016-frontend-maintenance-only](../../decisions/DEC-20261016-frontend-maintenance-only.md)).

## Primary paths

| Area | Files |
| --- | --- |
| Router + shell | `frontend/src/App.jsx` (routes, legacy redirects, review-count badge) |
| Domain lock | `frontend/src/context/DomainContext.jsx` (fixed to `maintenance`) |
| Navigation | `frontend/src/components/Sidebar.jsx` (maintenance destinations only) |
| API adapter | `frontend/src/api/client.js` (`maintenanceAPI`) |
| Pages | `pages/Assets.jsx`, `AssetHistory.jsx`, `ServiceRecords.jsx`, `Diagnostics.jsx`, `ReviewQueue.jsx`, `MaintenanceIngest.jsx`, `Graph.jsx`, `Settings.jsx`, `Landing.jsx` |
| Pure helpers | `frontend/src/utils/diagnostics.js` (error mapping, explanation recovery, `[UNVERIFIED]` split), `format.js` (dates), `loadError.js` |
| Tests | `frontend/src/test/*` (Vitest, API mocked) |
| Runtime target | `frontend/.env.development` (staging) · override with local `.env.local` |

## Routes

`/app` → `/app/assets`. Maintenance routes: `assets`, `asset-history/:uuid[#record_id]`, `records[?asset=<uuid>]`,
`diagnostics`, `review-queue`, `maintenance-ingest`, `graph`, `settings`. `chat`, `decisions`, `ingest`, `alerts`
and unknown paths redirect to `/app/assets`.

## Contracts the UI relies on

- `GET /maintenance/assets/{id}/history` is keyed by the asset **UUID**; a tail number returns 404.
- Diagnose request `{asset_id (UUID), symptom_text}`; fields read: `ranked_checks[]` (`part_name`, `evidence_count`, `sources`,
  `evidence_record_ids`), `evidence[]`, `rare_cases[]`, `explanation`, `context_size`, `citation_validation`
  (`valid_ids`, `invalid_ids`, `all_valid`), `warnings`. Frozen field list: `docs/mid1/12_u4_u5_diagnostics_handoff.md`.
- Copilot turn carries optional asset/session IDs, a bounded message, and the
  current case state. The page defaults to fleet-wide chat and retains the
  one-shot UI under **Quick diagnose**.
- Review queue rows carry `classification_label`, `classification_rationale`, `confidence`, `candidates_considered`, `history_size`; coverage comes from `/maintenance/analysis/status`.
- Service Records consumes paginated `/maintenance/records`; Corrections consumes `/maintenance/corrections`.
- `GET /maintenance/records/{id}` re-runs the conflict engine (a model call) each time it is viewed.

## Behaviour rules (do not weaken)

| Rule | Where |
| --- | --- |
| Never substitute a made-up answer: 503 / 5xx / network / 404 / 422 / empty evidence each have their own message | `Diagnostics.jsx`, `utils/diagnostics.js` |
| "Citations verified" only when `all_valid` and no invalid IDs; wording says IDs exist, not that statements are supported | `Diagnostics.jsx` |
| Ranking is labelled as historical frequency, never a probability; decision-support notice on every result | `Diagnostics.jsx` |
| Missing model output is stated ("No written explanation returned"), not silently omitted | `Diagnostics.jsx` |
| Copilot `reply:null` is a visible model-unavailable state while deterministic ranking/evidence remain visible | `Diagnostics.jsx` |
| Copilot sessions use guarded `localStorage`; storage failure does not disable the page | `Diagnostics.jsx` |
| **Reflect, never hide or alter, what Umar/Usman's backends return.** Shown as sent: rank `score` (labelled "rank score", not a probability), `context_size.wall_clock_s`, every `evidence_record_ids` entry (expandable), the model's text even when no evidence exists (labelled unsupported), `confidence` / `jasc_code` / `source` on history, JASC on the records list, and the `/api/health` runtime flags + `git_sha` on Settings. A field the backend did not send is omitted, never shown as `false`/`No` | [DEC-20261016-frontend-reflects-backend-outputs](../../decisions/DEC-20261016-frontend-reflects-backend-outputs.md) |
| Review Accept/Reject change real data: the screen changes only after the server confirms; no bare-key shortcuts | [DEC-20261016-review-actions-server-confirmed](../../decisions/DEC-20261016-review-actions-server-confirmed.md) |
| Load failures are shown as failures, never as "empty" | `AssetHistory.jsx`, `ReviewQueue.jsx`, `ServiceRecords.jsx` |
| Unscored and API-flagged legacy placeholders never show a number; no-conflict shows comparison count; relation scores are labelled heuristic/not probability; superseded shows backend `corrected_by` only | `ConfidenceBar.jsx`, `AssetHistory.jsx`, `ServiceRecords.jsx` |
| Only backend-supplied values are displayed (no invented supersession reason, no "Invalid Date") | `AssetHistory.jsx`, `utils/format.js` |
| No UI control may wipe the graph (Settings reset removed) | `Settings.jsx` |
| Ingest writes only after an explicit confirm; counts are the backend's own numbers; failures are inline, never `alert()` | `MaintenanceIngest.jsx`, `CsvUploader.jsx`, `IngestResult.jsx`, [DEC-20261017-ingest-csv-upload-ui](../../decisions/DEC-20261017-ingest-csv-upload-ui.md) |
| Graph shows only stored edges for one aircraft; counts are what is drawn; `SUPERSEDES` is styled apart; no invented edges | `Graph.jsx`, `utils/graphScope.js`, [DEC-20261017-graph-aircraft-focus](../../decisions/DEC-20261017-graph-aircraft-focus.md) |

## Performance

- Assets: one `GET /maintenance/assets` (staging 0.99 s for 118 aircraft after the backend aggregation fix).
- Service Records: defaults to **All aircraft** and makes two page-initiated
  calls (asset options + first paginated record page), with no per-aircraft
  fan-out ([DEC-20261017-fleet-service-records](../../decisions/DEC-20261017-fleet-service-records.md)).
  The app shell adds one `review-queue` call for the sidebar badge on every page, then polls every 30 s.
- Diagnostics: fresh diagnoses and copilot turns call the model and can be slow;
  the UI sets no request timeout. Copilot state is bounded by backend list and
  message limits.

## Environment

`npm run dev` reads `frontend/.env.development` (shared staging). For a local backend create `frontend/.env.local`
with `VITE_API_URL=/api` and `VITE_PROXY_TARGET=http://localhost:8000`. **Check before committing: `.env.local` is not
currently listed in `.gitignore`** despite what other docs say. Asset UUIDs differ between local Neo4j and staging, so
deep links containing a UUID are environment-specific.

## Tests

`npm test` (123 tests at 2026-10-17) and `npm run build`. Tests mock the API: they prove UI behaviour per response
shape, not live integration. There is no linter. Evidence and live checks: `docs/mid1/02_frontend_evidence.md`.

## Open / known

- `npm audit --omit=dev`: 2 moderate react-router 6.x advisories remain; the fix is react-router 7 (breaking). See
  deferred scope.
- 2026-10-16 observation: on shared staging, fresh diagnose calls returned an empty `explanation`, empty `evidence` and
  empty citation lists (3 of 3 symptoms) while the ranking was present; the same merged code run locally returned a full
  explanation for 1 of 2. **Settings now shows staging's pinned model as `openai/gpt-oss-20b`; the local stack uses
  `openai/gpt-oss-120b`**, a likely (unconfirmed) cause. Needs staging logs / `GROQ_MODEL` on the VM. The UI shows the notice above.
