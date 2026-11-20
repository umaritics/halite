# Investigation frontend integration handoff

Status: **proposal, not applied**. Shared frontend preparation has not landed.
The user has authorized preparing the integration for review. A separate branch
will apply and verify it; no Shahmeer review or merge approval is fabricated.

`FRONTEND_INTEGRATION.patch` is the concrete minimum registration proposal:

- Shared `src/app/registry.js` discovers feature manifests once.
- App mounts their routes under the existing authenticated shell and defaults to home.
- Sidebar renders their navigation and removes the old local-Copilot destination.
- AuthContext clears both unowned legacy browser keys on authentication and logout.
- Login/invite defaults point to home; saved explicit destinations still take precedence.
- Sidebar's destination assertion follows the new navigation labels.

The patch passes `git apply --check` against this branch but is intentionally not
applied to shared owner files. Shahmeer may incorporate it into his preparation
PR or review/authorize this small handoff. His broader frontend cleanup, UI
primitives, global client split, error boundary and chart library stay his work.
After his registry lands, the investigation/home feature files need no new shell
edits: their manifests already carry the agreed routes and nav entries.

The runnable preview at `frontend/e2e/investigation-preview.html` proves the
feature workflow independently, using real authentication and a disposable local
API/Neo4j/PostgreSQL. It is **not** evidence that production App/Sidebar routing
or global logout cleanup has shipped. The main application still exposes its old
diagnostics screen until the integration is accepted. Existing old Copilot tests
therefore remain intact; new feature tests cover the replacement workflow.

Acceptance after applying the handoff: run all frontend tests/build, add explicit
App redirect and global logout migration tests, then exercise the production
BrowserRouter path (not only the hash-router preview). Auth/invite navigation
tests may need an explicit home test route where they currently only declare an
assets test destination. Do not weaken their authentication assertions.
