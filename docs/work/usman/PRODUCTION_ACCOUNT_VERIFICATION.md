# Production test-account access

Verified on 2026-11-22 against the shared public backend using the dedicated
account explicitly authorized by Usman. Credentials and returned tokens were
held in process memory and are excluded from this record and project files.

| Check | Observed result |
| --- | --- |
| Login with the newer supplied candidate | HTTP 401 |
| Login with the earlier supplied candidate | HTTP 200; access token present; admin role |
| Authenticated `GET /api/auth/me` | HTTP 200 |
| Authenticated `GET /api/sessions` | HTTP 200 |
| Exploratory `GET /api/experiments` | HTTP 404; this path is not an established research API contract |
| Explicit logout of the verification session | HTTP 200 |

No maintenance data, user roles or passwords were changed. This proves API login
and authenticated access, not signed-in browser acceptance, refresh persistence,
research rendering or session creation. Those product checks remain separate.
The earlier credential is the working candidate; avoid retrying the rejected
candidate and consuming the account's lockout allowance.

## Prepared public browser instrument

Added `frontend/e2e/verify-production-site.cjs` and a separate manual main-only
workflow. Fixed origins, exact deployed SHA, real research artifact parity,
home/history, session renewal, phone geometry, both themes and logout are checked.
Only authentication POSTs are allowed; no new model call or maintenance write.
The workflow expects encrypted dedicated-account secrets. Local browser execution
is intentionally avoided following the machine incident. Syntax validation and
actual hosted execution are separate gates; neither is inferred from preparation.

Instrument source `0b8f7cb` passed full hosted CI `44986105585`: backend 531
tests with zero failures/errors/skips; 5,540/6,739 = 82.21% measured coverage;
frontend tests/builds and disposable Neo4j/PostgreSQL/API/browser smoke all passed.
Raw CI metadata/XML are retained in `evidence/phase23-report-figures/`.
This CI does not access the production account and is not a public browser pass.

PR54 now merged as `db574acadd4caf5cf60be45559708c82319711a6` after source
`c330480` passed CI44988236394 (534 backend tests;82.22% measured core coverage;
all jobs passed). The original model measurement is terminal, so its merge hold
is released. Main CI44988523496 and ordinary deployment must succeed before the
new manual browser workflow runs. Prepared/merged code is not a browser pass.

Actual merged-main CI44988523496 and deploy44988762837 passed; public health
confirmed db574ac and2,079records. Hosted real signed-in browser44988921561 then
passed; six screenshots and sanitized JSON were inspected/hash-checked. See
PUBLIC_BROWSER_VERIFICATION.md for exact scope. Login, chart/data parity,
home/history reads, refresh, phone layout, both themes and logout are proven;
empty history does not establish production lifecycle or model responses.
