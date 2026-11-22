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
