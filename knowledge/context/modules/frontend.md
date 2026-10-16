---
id: mod-frontend
title: Frontend maintenance UX
status: active
owners: [Shahmeer]
updated: 2026-10-16
---

# Module: Frontend (maintenance)

## Purpose

Maintenance-only technician UX for assets, history, diagnostics, review queue, ingest, settings.

## Primary paths

| Area | Files |
| --- | --- |
| Router | `frontend/src/App.jsx` |
| API adapter | `frontend/src/api/client.js` (`maintenanceAPI`) |
| Diagnostics | `frontend/src/pages/Diagnostics.jsx` |
| Review | `frontend/src/pages/ReviewQueue.jsx` |
| Assets / history | `frontend/src/pages/Assets.jsx`, `AssetHistory.jsx` |

## Mid-I expectations

- Bind to live maintenance APIs (no static fake assets as the demo path).
- Show loading / empty / 404 / 503 honestly.
- Evidence IDs open real record views.
- Isolate legacy software-domain screens from the Mid-I story.

## Known handoff (from Usman audit)

Frontend CI job was failing on ReviewQueue test mock (`getRecord` not mocked). See `docs/mid1/06_frontend_review_queue_handoff.md`. Client.js on `usman` tip already defines `getRecord`; failure is likely **test mock**, not missing client method.
