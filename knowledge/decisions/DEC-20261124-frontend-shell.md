---
id: DEC-20261124-frontend-shell
title: Frontend shell renders from feature manifests on a shared UI kit
status: accepted
owners: [Shahmeer]
updated: 2026-11-24
---

# DEC-20261124 — Frontend shell and UI kit

## Context

The plan of 20 November made each owner responsible for their own pages. `App.jsx` hard-wired nine pages and the
sidebar kept a static list, so three people would have edited the same two files. 3,202 lines were unreachable from
the app entry point, requests had no timeout, and each page copied its own header, error and empty markup.

## Decision

1. Every signed-in route and navigation entry comes from `frontend/src/features/*/manifest.jsx`, collected by
   `frontend/src/app/registry.js`. The contract is documented in `frontend/src/app/README.md`.
2. Pages live in feature folders: `assets`, `integrity`, `intake`, `graph`, `auth`, `landing`, `admin`, next to
   Usman's `investigation` and `home`. `src/pages/` no longer exists.
3. `src/api/http.js` owns the axios instance, the token refresh interceptor and a 30 second default timeout.
   Model-backed and ingest calls set longer timeouts per call; the graph overview allows 120 seconds.
   `src/api/client.js` stays as a barrel so existing test mocks keep working.
4. `src/components/ui/` is the shared kit. Pages use it for headers, buttons, tabs and loading, empty and error states.
5. The graph page is lazy-loaded and falls back to a text table when WebGL is missing or the viewer throws.

## Behaviour changes that came with it

- Assets shows an error with retry, and an empty state, instead of a blank page.
- The text filters on Service Records wait 300 ms before requesting.
- The server-path corpus ingest is shown to admins only and asks for confirmation.
- Review labels and statuses are shown as words in both themes; the hard-coded "recall 0.66" sentence is gone.
- The sidebar review badge refreshes after an accept or reject.
- Team & Access confirms a role change, a deactivation and an invite revocation, and shows a real error when the audit list fails.
- Settings shows placeholders while loading instead of a red error.
- A signed-out or expired session no longer tells the user to configure an environment variable.

## Consequences

- The old Diagnostics page, the evidence inspector and their 73 tests were removed. Frontend tests went from 283 to
  265: 73 removed with the dead code, 55 added.
- The main bundle went from 2,447 kB to 1,050 kB; the graph is a separate 1,396 kB chunk.
- Not yet checked in a browser: the look of the kit in dark and light themes, and the layouts at 1280 pixels and phone width.
- Built by an orchestrated run of coding agents on 24 November and reviewed by Shahmeer before merge.
