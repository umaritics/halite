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
is also enforced by AuthContext on the separate integration review branch.

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

On `codex/usman-ui-integration`, the shared registry discovers feature manifests;
App mounts them inside its authenticated shell, Sidebar renders their navigation,
and login/invite/app defaults point to home. The old Diagnostics URL redirects
to investigation history. This authorized preparation is pending owner review. The isolated `/e2e/investigation-preview.html` uses the real
AuthProvider, API and protected feature routes on disposable local services.
It proves the independent feature flow. A separate production-shell browser
mode verifies ordinary BrowserRouter URLs, refresh, redirects and global logout. The review patch
and user authorization are recorded in `docs/work/usman/FRONTEND_INTEGRATION.md`.

Tests: `InvestigationSessions.test.jsx`, `InvestigationQuick.test.jsx`,
`InvestigationApi.test.js`. Browser verifier: `frontend/e2e/verify-investigation-ui.cjs`.
The separate Vite preview build compiles every new feature even before App imports
them. Local browser evidence includes 1280px dark/light, two browsers, refresh,
outcomes/print, hidden foreign session, model-off quick diagnosis and widget outage.

## Decision-core display extension

New Copilot/session turns supply uncalibrated named beliefs, the other bucket and
entropy. The UI renders all of them as relative support and labels calibration
status. Old saved turns lacking beliefs retain their existing rendering; no
recomputation enriches historical responses. The default live policy remains unconfigured. The opt-in managed controller supplies official-code questions and saved posterior updates; experimental settings are explicitly labelled. Question IDs are submitted and changing identity resets the selection. Component and built-browser evidence is in `phase4-*`.

## Responsive shared-shell review integration

The user separately authorized applying/testing the App/Sidebar phone layout
patch. At 390px viewport, the icon rail is 64px and leaves a measured 326px main
area; the active answer input spans 260px and stays within the viewport. Desktop
keeps its measured 256px sidebar. Labels remain accessible, navigation can scroll,
roles/badges are retained, and sign-out waits for the existing auth operation.
The production-built browser submits the answer at phone width, verifies posterior
replay, keyboard navigation and sign-out/protected deep-link behavior. Source
changes are confined to the proposed App/Sidebar patch; Shahmeer review/merge
remain pending. See `phase7-*` evidence and `MOBILE_SHELL_HANDOFF.md`.

## Sentence-audit extension

Managed sessions and quick diagnosis now supply additive sentence audits and exact
source narratives. The UI preserves original Markdown, displays pending or explicit
experimental status, exposes sentence reasons and opens saved citation text.
No accepted support threshold or safety whitelist is fabricated. See
[investigation_grounding.md](investigation_grounding.md) and
[FLOW-grounding.md](../../flows/FLOW-grounding.md) for calibration and replay rules.

## Research results product page

`ResearchPage.jsx` registers `/app/investigations/experiments` before the session-ID
route and is linked from investigation history. It loads the authenticated
experiments endpoint through the shared client with 15-second timeout and abort
on identity change. Loading, explicit empty, unavailable/retry and signed-out
states do not show fabricated measurements.

The page reads all three saved question policies, three attribute controls,
part-change cohorts and top-1/top-3/entropy (bits) metrics. It displays the paired
information-gain-minus-random interval at the last recorded budget, including
zero-crossing uncertainty. Two saved abstention charts show accuracy–coverage and
the top-3 outcome-key proxy. The verified frozen test is now the default view;
selection and historical pre-question studies are separate evidence-set choices.
The runtime policy is unaffected. Method versions, corpus split, ECE interval and
publication/artifact hashes remain visible. Shared primitives and Recharts
wrapper are isolated on the preceding owner-review branch.

`InvestigationResearch.test.jsx` tests loading, real-artifact chart parity,
controls, failure/retry/empty states and account-change cancellation. Hosted
`e2e/verify-research-ui.cjs` checks the production build against the disposable
Compose API, SVG whiskers, table parity, deep-link reload and both themes at
1280px and 390px. Its outage/empty subchecks explicitly mock those responses;
normal publication reads use the real authenticated endpoint.

Verified research-page source `ecdc264`: hosted workflow 44856875802 passed
445 backend/275 frontend tests, builds, real-graph/session smoke and production
browser checks, including exact recorded budget ticks and phone geometry.
Retained proof: `docs/work/usman/evidence/phase10-research-panel/`.

## Final frozen research publication (v2)

The default 2025 view reads the saved three-control question-budget curves and
fixed stopping comparisons, with primary/post-selection-label and part-change
controls. It shows chosen/off metrics and exact 95% intervals, valid bootstrap
draws, named-top ECE, candidate misses, proxy definitions and prior-prototype
exposure. Zero-answer accuracy stays undefined. No test threshold curve is
invented. The 2024 question-conditioned view reads only the frozen .50-bit gain
slice; its accepted .80 point is marked solely on the all-attribute IG/all-case
curve. The earlier pre-question study remains available without that marker.

The v2 API checks the actual frozen policy/protocol and independent test receipt;
it returns saved values and provenance only. The page performs no experiment or
runtime activation. Shared ResearchChart gains an optional stage label (default
selection), so held-out figures are not mislabelled. This small shared follow-up
is prepared for Shahmeer review in CHART_FOUNDATION_REVIEW.md. Phase18 synthetic,
artifact-contract and full hosted browser verification is pending.
