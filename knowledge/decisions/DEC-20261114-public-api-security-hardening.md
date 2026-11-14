---
id: dec-public-api-auth-hardening
title: Global API key authentication, fail-closed startup, Gitea retirement, and container sandboxing
status: accepted
owners: [Umar, Usman, Shahmeer]
updated: 2026-11-14
---

# DEC-20261114 — Harden public Halite API after shared-VM Gitea incident

## Status

`accepted` (post-Mid-I security hardening across backend, container, deploy, and frontend client adapter).

## Context

On the shared VM (`dev1.corp.curatech.pk`), a separate Gitea container exposed on the public internet was compromised via open registration/API abuse to run an in-container cryptominer. Gitea has been removed from the host, while Halite intentionally remains reachable over HTTPS (`https://dev1.corp.curatech.pk/halite-api/*` -> `127.0.0.1:8002`) so the hosted React application and team workflows can reach the backend.

Previously, only `/api/ops/logs`, `DELETE /api/graph/reset`, and `POST /api/maintenance/analysis/run` checked `X-Ops-Token`. All other `/api/*` routes (`/api/chat`, `/api/maintenance/*`, `/api/graph/*`, `/api/ingest/*`, `/api/decisions/*`, `/api/webhook/gitea`), `/docs` + `/openapi.json`, wildcard `*.vercel.app` CORS, unrestricted server-side `csv_path` on `/api/maintenance/ingest`, and a root-user writable container remained exposed to anonymous callers.

## Decision

1. **Single primary client auth (`HALITE_API_KEY`):**
   - `api/security.py` defines `require_halite_api_key`, accepting `Authorization: Bearer <HALITE_API_KEY>` (primary) or `X-Halite-Api-Key: <HALITE_API_KEY>` (alias), verified via `secrets.compare_digest`.
   - `api/router.py` mounts all protected routers under one parent `/api` `APIRouter` carrying `Depends(require_halite_api_key)` — shared identically between `main.py` and `tests/conftest.py`.
   - **Fail closed:** Whenever `DEMO_MODE=false` and `HALITE_API_KEY` is unset, protected routes return `503 Service Unavailable` instead of running open. In `DEMO_MODE=true` with empty `HALITE_API_KEY`, local unit tests keep working without secrets.
2. **Explicit public allowlist & OpenAPI gating:**
   - Only `GET /health`, `GET /api/health`, and `GET /api/ops/version` are public (rate-limited, metadata only).
   - `/docs`, `/redoc`, and `/openapi.json` default off (`404`) when `DEMO_MODE=false` unless `EXPOSE_OPENAPI=true`.
3. **Two-tier secret boundary (`HALITE_API_KEY` vs `OPS_TOKEN`):**
   - `OPS_TOKEN` (`X-Ops-Token`) remains strictly for privileged/destructive operator actions (`/api/ops/logs`, `DELETE /api/graph/reset`, `POST /api/maintenance/analysis/run`) and is never placed in frontend env files.
   - Supplying a valid `X-Ops-Token` also satisfies the parent `/api` auth gate so operators do not need two headers.
4. **Retire Gitea surface & close path/CORS/rate vectors:**
   - `/api/webhook/gitea`, `/api/ingest/gitea`, and `/api/ingest/code` return `410 Gone` unless `ENABLE_GITEA_INTEGRATION=true` (and webhook fails closed `503`/`401` without valid HMAC-SHA256).
   - `POST /api/maintenance/ingest` jails `csv_path` inside `MAINT_DATA_DIR` or `tests/fixtures`.
   - `CORS_ORIGIN_REGEX` narrows from `https://.*\.vercel\.app` to `^https://halite(?:-[a-z0-9-]+)?\.vercel\.app$`.
   - Bounded in-memory sliding-window rate limits throttle per-IP API bursts, LLM quota routes, and `401` brute-force attempts (reading rightmost `X-Forwarded-For` from loopback Caddy only).
5. **Container sandbox (`Dockerfile` + `docker-compose.vm.yml`):**
   - Run as non-root `10001:10001`, `read_only: true` rootfs, `tmpfs` with `noexec,nosuid,nodev` on `/tmp` and `/app/data`, `cap_drop: ALL`, `no-new-privileges:true`, and `pids_limit: 128`.
6. **Frontend client (`frontend/src/api/client.js`):**
   - Sends `Authorization: Bearer <VITE_HALITE_API_KEY>` via Axios request interceptor and exposes `setSessionTokenGetter` so upcoming user login/JWT tokens seamlessly override the static key.

## Consequences

- Anonymous scanners hitting `dev1.corp.curatech.pk/halite-api/api/*` receive `401` (or `404` on `/docs`, `410` on Gitea webhooks, `429` under flood) before touching Neo4j or Groq.
- Developers and Vercel deployments must configure `VITE_HALITE_API_KEY` (and optional GitHub Actions secret `HALITE_API_KEY` for remote post-deploy smoke; VM `remote_deploy.sh` always verifies authenticated + unauthenticated gates directly).
- Full runbook lives at [`docs/security-public-deployment.md`](../../docs/security-public-deployment.md).

## Owners

Umar, Usman, Shahmeer (cross-cutting security hardening requested by project lead Umar).
