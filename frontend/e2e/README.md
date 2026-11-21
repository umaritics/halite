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

## Managed question flow

`verify-question-ui.cjs` exercises the actual built App against a disposable local
API and real Neo4j/PostgreSQL. It refuses non-loopback hosts. Enable the backend
with `SESSION_QUESTIONS_ENABLED=true` and an absolute `SESSION_POLICY_FILE` pointing
to `backend/tests/fixtures/question_policy_experimental.json` for **synthetic
verification only**. This fixture deliberately forces questions; it is not a
selected operating point and must not be silently used as production configuration.
The flag defaults off and invalid enabled configuration fails explicitly.

Use the same admin/browser evidence variables as the existing verifier. The
synthetic CSV defaults to `backend/tests/fixtures/question_smoke.csv`; the API
allows server-side ingest from its tests/fixtures directory. An arbitrary `/tmp`
path is intentionally rejected. Build with `VITE_API_URL` set to the local API.
The proof covers official option labels/gain, changing support after an answer,
not-sure, saved-question identity, three-question budget and exact read-only replay.
It writes no credentials or tokens.

`HALITE_UI_EVIDENCE_PREFIX` separates evidence runs. Geometry is recorded in the
JSON; `HALITE_UI_REQUIRE_MOBILE_LAYOUT=true` additionally requires at least 280px
for the main content at 390px viewport width. The initial shared shell fails this
usability check even though it has no document overflow. The user-authorized
separate responsive-shell patch is documented in `MOBILE_SHELL_HANDOFF.md`.
