# Halite — Public API Security & VM Deployment Runbook

This document defines the threat model, authentication contract, container sandbox, reverse-proxy boundary, and operator runbook for running the Halite FastAPI backend at a public HTTPS URL (`https://dev1.corp.curatech.pk/halite-api/...`) behind Caddy.

---

## 1. Threat Model & Context

Following the November 2026 incident on the shared VM (where an internet-exposed Gitea container was abused via open registration/API access to spawn an in-container cryptominer), Halite enforces **defense in depth**:

1. **Public HTTPS = hostile internet scanners.** `handle_path /halite-api/*` on port 443 is reachable by anyone on the internet. Reverse-proxy TLS and localhost port binding (`127.0.0.1:8002:8000`) protect the raw Docker port from direct WAN scans, **not** the HTTP routes Caddy forwards.
2. **High blast radius inside the app.** Unauthenticated access to `/api/maintenance/*`, `/api/chat`, or `/api/graph/*` would allow anonymous callers to:
   - burn Groq LLM quota and trigger external billing/rate exhaustion;
   - exfiltrate or mutate Neo4j AuraDB maintenance records and conflict state;
   - upload arbitrary documents/CSVs or probe filesystem paths.
3. **Defense-in-depth layers implemented:**
   - **Layer 1 — Edge (Caddy + UFW):** UFW allows only `22`, `80`, `443`. Caddy terminates TLS, enforces request body caps (`max_size 12MB`), strips `/halite-api`, sets HSTS/security headers, and proxies to `127.0.0.1:8002`.
   - **Layer 2 — Application Authentication & Fail-Closed Startup:** Every sensitive `/api/*` route sits behind a single parent `APIRouter` with `Depends(require_halite_api_key)`. If `DEMO_MODE=false` and `HALITE_API_KEY` is unset, protected routes fail closed with **HTTP 503** (never silently open).
   - **Layer 3 — Privilege Separation (`OPS_TOKEN`):** Destructive and operational endpoints (`GET /api/ops/logs`, `DELETE /api/graph/reset`, `POST /api/maintenance/analysis/run`) require `X-Ops-Token` (`OPS_TOKEN`), which is never embedded in browser builds.
   - **Layer 4 — Abuse & Quota Controls:** Bounded in-memory sliding-window rate limiting per client IP (rightmost hop from loopback proxy), stricter per-minute caps on LLM-backed endpoints, brute-force lockout on repeated `401` failures, server-side CSV path jailing, and unregistered Gitea endpoints (`404 Not Found`).
   - **Layer 5 — Container Sandbox (`docker-compose.vm.yml` + `Dockerfile`):** Non-root UID/GID `10001:10001`, `read_only: true` root filesystem, `noexec,nosuid,nodev` `tmpfs` mounts (`/tmp`, `/app/data`), `cap_drop: ALL`, `no-new-privileges:true`, `pids_limit: 128`, CPU/memory caps, and bounded JSON logs. Even if a dependency vulnerability were exploited, binary drops and fork-bombs inside the container are blocked by kernel enforcement.
   - **Layer 6 — Private local LLM (staging):** Ollama runs as `halite-ollama` with **no host `ports:`**, `OLLAMA_API_KEY`, and RAM/CPU limits. Only `halite-api` on the Docker bridge may call `http://halite-ollama:11434/v1`. Public callers still pass through Layer 2 (`HALITE_API_KEY` / JWT). See [`local-llm-staging.md`](local-llm-staging.md).

---

## 2. Route Policy (Explicit Allowlist)

| Class | Routes | Auth Requirement | Notes |
| --- | --- | --- | --- |
| **Public** | `GET /health`, `GET /api/health`, `GET /api/ops/version` | None (rate-limited) | Build SHA + boolean readiness flags only; never exposes secrets or record payloads |
| **OpenAPI / Docs** | `GET /docs`, `GET /redoc`, `GET /openapi.json` | Disabled (`404`) when `DEMO_MODE=false` | Controlled by `EXPOSE_OPENAPI` (`false` on public VM) |
| **Retired Webhooks** | `POST /api/webhook/gitea` | Unregistered (`404`) | Full retirement removes the handler; legacy environment flags do not restore it |
| **Authenticated Client Surface** | All other `/api/*` (`maintenance/*`, `diagnostics`, `graph/*`, `chat`, `decisions/*`, `ingest/document`, `alerts/*`, `domains`) | `Authorization: Bearer <HALITE_API_KEY>` (primary) or `X-Halite-Api-Key: <HALITE_API_KEY>` (alias) | Constant-time `secrets.compare_digest`; returns `401` on missing/wrong key, `503` if unconfigured in non-demo mode |
| **Privileged Operator Surface** | `GET /api/ops/logs`, `DELETE /api/graph/reset`, `POST /api/maintenance/analysis/run` | `X-Ops-Token: <OPS_TOKEN>` | Separate server/operator secret; valid `X-Ops-Token` also satisfies the parent `/api` gate so operators only need one header |

> **Retired Gitea ingest routes:** `POST /api/ingest/gitea` and `POST /api/ingest/code` are also unregistered (`404`), including when old enable flags are present.

---

## 3. Environment Variables Reference

Configure secrets in `/home/umar/halite/backend/.env` on the VM (`chmod 600`), never in Git.

| Variable | Scope | Default | Production / VM Requirement |
| --- | --- | --- | --- |
| `DEMO_MODE` | Backend | `true` | Must be `false` (enforced in `docker-compose.vm.yml`) |
| `HALITE_API_KEY` | Backend | `""` | **Required** (`>= 32` random URL-safe bytes). Unset + `DEMO_MODE=false` => HTTP `503` on `/api/*` |
| `OPS_TOKEN` | Backend | `""` | **Required for ops** (`>= 32` random URL-safe bytes, distinct from `HALITE_API_KEY`). Unset => HTTP `503` on ops/reset routes |
| `EXPOSE_OPENAPI` | Backend | `None` (`true` in demo, `false` in prod) | Set `false` on public VM |
| `FRONTEND_URL` | Backend | `http://localhost:5173` | Primary production web origin (e.g., `https://halite.vercel.app`) |
| `CORS_ALLOWED_ORIGINS` | Backend | `""` | Optional comma-separated extra origins |
| `CORS_ORIGIN_REGEX` | Backend | `^https://halite(?:-[a-z0-9-]+)?\.vercel\.app$` | Scoped strictly to Halite Vercel deployments (not arbitrary `*.vercel.app` tenants) |
| `RATE_LIMIT_ENABLED` | Backend | `true` | Keep `true` on public VM |
| `RATE_LIMIT_API_PER_MINUTE` | Backend | `180` | Per-IP sliding-window limit across `/api/*` |
| `RATE_LIMIT_LLM_PER_MINUTE` | Backend | `20` | Per-IP sliding-window limit on Groq/model routes (`diagnose`, `copilot/turn`, `chat`, conflict `records`) |
| `RATE_LIMIT_AUTH_FAILURES_PER_MINUTE` | Backend | `20` | Per-IP lockout threshold for `401` brute-force attempts |
| `ENABLE_GITEA_INTEGRATION` | Backend | `false` | Deprecated compatibility setting; does not restore removed routes |
| `GITEA_WEBHOOK_SECRET` | Backend | `""` | Deprecated compatibility setting; no active webhook handler |
| `VITE_API_URL` | Frontend | `https://dev1.corp.curatech.pk/halite-api/api` | Points SPA at Caddy reverse-proxy path |
| `VITE_HALITE_API_KEY` | Frontend (`.env.local` / Vercel env) | `""` | Sent as `Authorization: Bearer <key>` by `frontend/src/api/client.js` |

---

## 4. Website User Authentication, RBAC & Server-to-Server Keys

Halite implements **Module M01 (Workspace & Identity)** directly in FastAPI backed by PostgreSQL (`halite-postgres` on `dev1`, or any Supabase PostgreSQL URI via `DATABASE_URL`):

- **Zero static API key in public browser builds:** Website users sign in at `/login` (or activate a single-use 72-hour admin invitation at `/accept-invite?token=...`). The browser holds a 15-minute `HS256` Access JWT in memory (`Authorization: Bearer <jwt>`) and rotates a single-use hashed Refresh Session (`HttpOnly; Secure` cookie + `sessionStorage` fallback for Safari/Brave ITP). `VITE_HALITE_API_KEY` is therefore **not** needed in hosted Vercel builds (`HALITE_API_KEY` stays strictly server-to-server).
- **Argon2id + Lockout + Token-Family Theft Detection:** Passwords use Argon2id with constant-time dummy verification for unknown emails and 5-attempt lockout (`429`). Replaying an already-rotated refresh token immediately revokes the entire session family.
- **Role-Based Access Control (RBAC):**
  - `technician`: Browse fleet assets/history/graph, upload/ingest maintenance records, and run Diagnostics & Copilot.
  - `supervisor`: All technician permissions **plus** `Accept` / `Reject` on `/api/maintenance/review-queue/{id}`, stamping `reviewed_by_*` onto Neo4j `ServiceRecord` nodes and writing immutable `audit_events` rows in PostgreSQL.
  - `admin`: All supervisor permissions **plus** `/app/team` (`/api/admin/users`, `/api/admin/invites`, `/api/admin/audit-events`) and batch conflict analysis.

---

## 5. Caddy Path Mapping & Operator Verification Runbook

Caddy uses `handle_path /halite-api/*` (which strips `/halite-api` before forwarding to `127.0.0.1:8002`):

- External client calls `https://<host>/halite-api/api/health` -> FastAPI receives `GET /api/health` (`200 OK`).
- External client calls `https://<host>/halite-api/health` -> FastAPI receives `GET /health` (`200 OK`).
- External client calls `https://<host>/halite-api/api/maintenance/assets` -> FastAPI receives `GET /api/maintenance/assets` (`401` without Bearer key, `200` with Bearer key).

### Generate & rotate keys on the VM

```bash
ssh umar@dev1.corp.curatech.pk
python3 -c "import secrets; print('HALITE_API_KEY=' + secrets.token_urlsafe(36))"
python3 -c "import secrets; print('OPS_TOKEN=' + secrets.token_urlsafe(36))"
# Edit /home/umar/halite/backend/.env (chmod 600) and recreate container:
cd /home/umar/halite
docker compose -f docker-compose.vm.yml up -d --build --force-recreate
```

### External verification checklist (`curl`)

```bash
BASE="https://dev1.corp.curatech.pk/halite-api"

# 1. Public health & version -> 200
curl -i "$BASE/health"
curl -i "$BASE/api/ops/version"

# 2. Anonymous API calls -> 401 Unauthorized
curl -i -X POST "$BASE/api/chat" -H "Content-Type: application/json" -d '{"message":"ping"}'
curl -i "$BASE/api/maintenance/assets"

# 3. OpenAPI / Swagger UI -> 404 Not Found
curl -i "$BASE/docs"
curl -i "$BASE/openapi.json"

# 4. Retired Gitea webhook -> 404 Not Found
curl -i -X POST "$BASE/api/webhook/gitea" -d '{}'

# 5. Authenticated client call -> 200 OK
curl -i -H "Authorization: Bearer <HALITE_API_KEY>" "$BASE/api/maintenance/assets"

# 6. Privileged ops logs -> 401 with client key, 200 with X-Ops-Token
curl -i -H "Authorization: Bearer <HALITE_API_KEY>" "$BASE/api/ops/logs?lines=20"
curl -i -H "X-Ops-Token: <OPS_TOKEN>" "$BASE/api/ops/logs?lines=20"
```

After full legacy retirement, `/api/webhook/gitea` is unregistered and returns
404. Both VM-local and public release probes require404; they no longer expect
the earlier disabled-handler410. A cross-layer test compares both release
expectations with the actual router response. Authenticated/anonymous asset,
closed docs, PostgreSQL and exact-version checks remain unchanged.
