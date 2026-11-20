# Investigation integration preview

Start the normal local API with disposable Neo4j/PostgreSQL and a bootstrapped
user, then start Vite with `VITE_API_URL=/api` and
`VITE_PROXY_TARGET=http://127.0.0.1:18000`. Open
`/e2e/investigation-preview.html`. This harness uses the real shared AuthProvider,
HTTP client and protected routes with the investigation/home feature manifests.
It is a development integration harness, not production route registration.

No credentials or tokens are embedded. Sign in through the ordinary login screen.
Shared App/Sidebar/AuthContext changes require the handoff described in the plan;
this harness allows end-to-end verification while that handoff is pending.

Build the feature preview independently with
`npx vite build --config e2e/vite-preview.config.mjs`. This compiles the new
manifests, quick diagnosis and workspace rather than relying on the existing
production entry point to import unregistered features. Output goes to the
 task-owned `/tmp/halite-investigation-preview-dist` folder.

The Playwright verification script accepts `HALITE_PLAYWRIGHT_MODULE` (a standard
Playwright installation or the Codex bundled path), `HALITE_CHROME_EXECUTABLE`,
`HALITE_UI_ADMIN_EMAIL`, `HALITE_UI_ADMIN_PASSWORD`, and `HALITE_UI_EVIDENCE_DIR`.
It refuses non-loopback hosts and creates only synthetic users/investigations.
No credentials, cookies or bearer tokens are written to its evidence files.

Set `HALITE_UI_PRODUCTION_SHELL=true` to run the same verifier through ordinary
`/login` and `/app/*` BrowserRouter routes. This mode additionally checks the old
Diagnostics redirect, global logout storage cleanup, the protected deep link
after logout and subsequent login as another technician. Evidence is written to
`phase3-integration-*`, separately from the independent preview. It uses the
actual App/Sidebar/AuthContext; it is local verification, not staging deployment.
