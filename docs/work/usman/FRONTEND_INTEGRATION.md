# Investigation frontend integration review

Status: **prepared and locally verified on `codex/usman-ui-integration`**.
The user explicitly authorized **“Prepare the integration for review.”**
Shahmeer owner review and merge remain pending; broader shared frontend
preparation remains his work.

The branch is stacked on `codex/usman-investigation-ui` (PR #29), which contains
the independently verified feature package. `FRONTEND_INTEGRATION.patch` preserves
the initial registration proposal for review history; the branch diff is the
authoritative implementation, including the added integration tests.

- Shared `src/app/registry.js` discovers feature manifests once.
- App mounts their routes under the authenticated shell and defaults to home.
- Sidebar renders their navigation and removes the old local-Copilot destination.
- AuthContext clears both unowned legacy browser keys on authentication and logout.
- Login/invite defaults point to home; explicit saved destinations still win.
- No old unowned browser records are imported into an account.

## Executed verification

All **256 frontend tests in 25 files passed**. Includes actual App route
registration, old Diagnostics redirect, protected saved-session URL, failed
restoration/new login/logout privacy (including server logout failure), and invite
activation at home while preserving explicit protected destinations. Main
production build passed.

Chrome exercised the actual built production bundle (local Vite preview) and
App/Sidebar/AuthContext through BrowserRouter with a
real local API, Neo4j and PostgreSQL: ordinary login/home, create/turn/evidence,
closure/print, second-browser/reload without inference, outsider denial,
model-off quick diagnosis, partial summary outage, dark/light 1280px layouts,
old Diagnostics redirect, logout clearing and another account's protected deep
link. No page errors or horizontal overflow. Screenshots were visually inspected.
Evidence: `evidence/phase3-integration-*`. Runtime health honestly reports model
fallback. This proves local integration, not staging deployment, owner approval
or completion of the remaining research packages.

The independent preview remains available for feature-only testing. Shared
cleanup, client split, error boundary, chart library and UI primitives remain
outside this small authorized handoff.
