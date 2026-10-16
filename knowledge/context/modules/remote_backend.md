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

Create `frontend/.env.local` (gitignored):

```env
VITE_API_URL=https://dev1.corp.curatech.pk/halite-api/api
```

Then `npm run dev` / `npx vite --host 127.0.0.1 --port 5173`.  
Do **not** rely on the Vite proxy to localhost when using the shared backend.

## How backend updates reach the VM (CD)

Workflow: `.github/workflows/deploy-staging.yml`

Triggers:

- Push to `feat/mid1/graph-diagnostics`, `usman`, or `main` that touches `backend/**` (or compose/deploy scripts)
- Manual **Actions → Deploy staging backend → Run workflow**

What it does: SSH into the VM → `git fetch/checkout` SHA → `docker compose -f docker-compose.vm.yml build/up` → verify public `/api/health`.

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

3. Settings → Environments → create **`staging`** (used by deploy workflows).
4. Push a backend change (or Actions → **Deploy staging backend** → Run).

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
| Push backend changes; let CD deploy | SSH into the VM “just to restart” |
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
