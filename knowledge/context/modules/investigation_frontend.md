---
id: mod-investigation-frontend
title: Account-scoped investigation interface
status: active
owners: [Usman]
updated: 2026-11-20
---

# Investigation and home features

`frontend/src/features/investigation/` provides server-backed history, workspace,
closure, printable reports, quick diagnosis and rendering for future decision,
belief, question and grounding fields. `features/home/` provides the three-summary
dashboard and the current user's recent investigations. Each exports a manifest
with the routes/nav specified in `docs/plan/CONTRACTS.md`.

## Data and privacy

History lists, filters and cursors come from the sessions API. The client sends
only the new message or a structured answer; it never replaces persisted case
state. Creation/closure update the interface only after server confirmation.
Closed/supervisor-owned views have no write controls. The shared HTTP instance
supplies JWT/refresh behavior; feature reads have 15s timeouts, model calls 300s.

Component instances are keyed by account/organisation and session ID. Reads abort
on scope changes; late writes cannot render after unmount. The old unowned local
workspace/session keys are cleared, never imported. The new feature saves no
investigation text, history or draft in localStorage. Global login/logout cleanup
requires the separately reviewed AuthContext integration.

On a stale/uncertain write, the user must reload before sending again. Drafts are
retained on failure and cleared after reload only if the server's latest saved
turn proves the same text was committed. No automatic mutation retry is performed
by the feature. Server concurrency controls remain authoritative.

## Evidence and decisions

Past turns replay their exact saved response and original narratives. Selecting
an older turn switches ranking/evidence to that snapshot; it never enriches saved
narratives with changed live graph data. Missing narratives are labelled missing.
The latest case/decision response is shown without inventing fields. Unconfigured
policy and unchecked sentences are explicitly labelled. Belief bars say relative
support; no calibrated probability or measured result is claimed. Questions use
backend-provided options/reasons; sentence marks reflect backend labels.

Quick diagnosis opts into degraded mode and renders `fallback_explanation` when
`explanation` is null. Aircraft loading errors are visible. Its normal request
requires an aircraft and symptom. Printable reports are fetched with the shared
JWT client into a new window; a blocked pop-up/fetch failure is actionable.

## Home behavior

Retrieval, integrity and session summaries load independently with allSettled.
A failed widget is hidden; all-widget failure is an explicit error with retry.
Empty statistics are labelled absent, never invented as zero. Recent session
loading/errors/empty states are independent of summary loading.

## Registration and verification

Feature manifests are ready for the shared registry. Until the approved
integration is applied, the current production App still mounts the old
Diagnostics page. The isolated `/e2e/investigation-preview.html` uses the real
AuthProvider, API and protected feature routes on disposable local services.
It proves the feature flow, not production-shell registration. The review patch
and user authorization are recorded in `docs/work/usman/FRONTEND_INTEGRATION.md`.

Tests: `InvestigationSessions.test.jsx`, `InvestigationQuick.test.jsx`,
`InvestigationApi.test.js`. Browser verifier: `frontend/e2e/verify-investigation-ui.cjs`.
The separate Vite preview build compiles every new feature even before App imports
them. Local browser evidence includes 1280px dark/light, two browsers, refresh,
outcomes/print, hidden foreign session, model-off quick diagnosis and widget outage.
