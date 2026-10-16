---
id: DEC-20261016-shared-staging-cd
title: Centralized staging API + GitHub Actions CD
status: accepted
owners: [Umar, Usman]
updated: 2026-10-16
---

# DEC-20261016 — Shared staging CD

## Context

Partners lack VM SSH. The public VM was serving a stale pre-maintenance API. The team wants one shared backend instead of everyone running local APIs.

## Decision

1. Treat `https://dev1.corp.curatech.pk/halite-api` as the team staging API.
2. Add GitHub Actions `deploy-staging.yml` to deploy on backend pushes (plus manual dispatch).
3. Add `/api/ops/version` (public) and `/api/ops/logs` (OPS_TOKEN) so partners can verify SHA and read logs without SSH.
4. Add `fetch-staging-logs.yml` as a backup log path via Actions artifacts.
5. Document partner workflow in `knowledge/context/modules/remote_backend.md`.

## Consequences

- Deploy requires one-time admin secrets (`VM_SSH_*`, `VM_DEPLOY_PATH`) and VM `backend/.env` with `OPS_TOKEN`.
- Until secrets are set, the workflow fails loudly with setup instructions (cannot deploy from the agent alone).
- Frontend should use `VITE_API_URL` pointing at the shared API for integration testing.
