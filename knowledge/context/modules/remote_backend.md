---
id: mod-remote-backend
title: Shared remote staging backend
status: active
owners: [Umar, Usman]
updated: 2026-10-16
---

# Shared remote staging backend

## Goal

One **centralized** API for the whole team. Partners do **not** need VM SSH. They develop frontend (and optionally local backend for unit tests) against:

`https://dev1.corp.curatech.pk/halite-api`

## Public URLs

| URL | Purpose |
| --- | --- |
| `https://dev1.corp.curatech.pk/halite-api/api/health` | Runtime honesty (`graph_mode`, `llm_mode`, `git_sha`, …) |
| `https://dev1.corp.curatech.pk/halite-api/api/ops/version` | Which SHA is live |
| `https://dev1.corp.curatech.pk/halite-api/api/ops/logs` | Recent app logs (**token required**) |
| `https://dev1.corp.curatech.pk/halite-api/api/maintenance/*` | Mid-I maintenance APIs |
| `https://dev1.corp.curatech.pk/halite-api/api/maintenance/diagnose` | Diagnostics |

## Frontend: point at the shared API

**Versioned default:** `frontend/.env.development` sets  
`VITE_API_URL=https://dev1.corp.curatech.pk/halite-api/api`  
so `npm run dev` hits staging after pull + restart (see `docs/mid1/09_frontend_shared_api.md`).

Override only if you need a local backend: create gitignored `frontend/.env.local` with `VITE_API_URL=/api`.

## How backend updates reach the VM (CD)

Workflow: `.github/workflows/deploy-staging.yml`

Triggers:

- Successful full `CI` completion for the current `main` tip. A newer `main`
  tip invalidates an older automatic deployment.
- Manual **Actions → Deploy staging backend → Run workflow** with a full
  40-character SHA reachable from `main`, an operation (`deploy` or
  `rollback`), and the matching uppercase confirmation.

Both paths require a successful full CI run for the exact SHA and use the
existing `staging` environment. Repository administrators must configure that
environment with required reviewers; without that GitHub setting, YAML alone
cannot enforce human approval. The known Shahmeer frontend failure therefore
blocks deployment and is not bypassed.

What it does: validate the SHA and CI result → record the currently deployed
SHA from `/api/ops/version` → SSH into the VM → rebuild → require public
health/version to report the exact approved SHA.

### Approved rollback

1. Read the previous deployed SHA from the prior deployment log's **Record
   currently deployed revision for rollback** step (or verify the currently
   live SHA through `/api/ops/version` before a release).
2. Confirm that SHA is reachable from `main` and has a successful full CI run.
3. Manually dispatch with that full SHA, choose `rollback`, type `ROLLBACK`,
   and approve the protected `staging` environment review.
4. The same post-deploy health, exact-version, and assets checks must pass.

Never use a branch name or arbitrary ref for rollback.

### Current VM facts (already provisioned)

| Item | Value |
| --- | --- |
| Host | `dev1.corp.curatech.pk` |
| SSH user | `umar` |
| Deploy path | `/home/umar/halite` |
| Container | `halite-api` on `127.0.0.1:8002` (Caddy public `/halite-api`) |
| Dedicated CD key (local) | `%USERPROFILE%\.ssh\halite_github_deploy` (**not** your personal key) |
| Ops token (local copy) | `%USERPROFILE%\.ssh\halite_ops_token.txt` (share via password manager only) |

### Safe credential model (best practice)

**Do not put your personal SSH private key in GitHub.**

1. Use a **dedicated ed25519 key** only for Actions (`halite_github_deploy`).
2. Only that key’s **public** half lives in the VM `authorized_keys`.
3. Only that key’s **private** half lives in GitHub secret `VM_SSH_KEY`.
4. If leaked: delete the line from `authorized_keys` + rotate the GitHub secret — your personal laptop login key stays safe.
5. `OPS_TOKEN` is a separate shared team secret for `/api/ops/logs` — not an SSH credential.

### Add GitHub secrets (you run this)

**Option A — recommended (script, no paste into chat):**

```powershell
# requires: gh auth login
cd U:\Development\NexiumApps\Halite
.\scripts\vm\set_github_secrets.ps1
```

**Option B — GitHub UI:**

1. Open https://github.com/umaritics/halite/settings/secrets/actions  
2. Create repository secrets:

| Name | Value |
| --- | --- |
| `VM_SSH_HOST` | `dev1.corp.curatech.pk` |
| `VM_SSH_USER` | `umar` |
| `VM_DEPLOY_PATH` | `/home/umar/halite` |
| `VM_SSH_KEY` | entire contents of `%USERPROFILE%\.ssh\halite_github_deploy` (including `BEGIN`/`END` lines) |

3. Settings → Environments → create **`staging`**, add required reviewers,
   and prevent administrators from bypassing the protection rule.
4. Merge a reviewed change to `main`, or manually dispatch a validated,
   CI-green `main` SHA for an approved release/rollback.

Verify:

```bash
curl -s https://dev1.corp.curatech.pk/halite-api/api/health
curl -s https://dev1.corp.curatech.pk/halite-api/api/ops/version
curl -s https://dev1.corp.curatech.pk/halite-api/api/maintenance/assets
```

`maintenance/assets` must be **200**. `git_sha` should update after CD runs.

## Logs without VM access

### Option A — API (preferred)

```bash
curl -s "https://dev1.corp.curatech.pk/halite-api/api/ops/logs?lines=200" \
  -H "X-Ops-Token: <OPS_TOKEN shared by admin>"
```

Share `OPS_TOKEN` with teammates via a password manager — **never commit it**.

### Option B — GitHub Actions artifact

Actions → **Fetch staging backend logs** → Run workflow → download artifact `staging-backend-logs`.

## What partners should / should not do

| Do | Don’t |
| --- | --- |
| Merge reviewed changes to `main`; approve CI-green releases | SSH into the VM “just to restart” |
| Check `/api/ops/version` after deploy | Claim live Neo4j/LLM without reading `/api/health` |
| Use shared API from frontend `.env.local` | Commit `.env` / `OPS_TOKEN` / SSH keys |
| Run backend unit tests locally (`DEMO_MODE=true`) | Point local Vite at localhost and assume that is staging |

## Agent rules

- Before diagnosing “staging is broken”, call `/api/health` and `/api/ops/version`.
- After changing deploy/ops behavior, update this note + `knowledge/flows/FLOW-deploy.md`.
- Ownership: deploy secrets/VM admin primarily Usman/infra; ops API + CD wiring may be touched by Umar for Mid-I unblocking — record DECs.

## Related

- Flow: [FLOW-deploy.md](../../flows/FLOW-deploy.md)
- Compose: `docker-compose.vm.yml`
- Script: `scripts/vm/remote_deploy.sh`
