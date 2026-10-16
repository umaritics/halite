# Frontend → shared staging API (Mid-I)

Owner: Umar / team  
Date: 2026-10-16  
Branch: `umar/mid1-graph-diagnostics` (file also needed on partner branches after pull)  
Knowledge: [`remote_backend.md`](../../knowledge/context/modules/remote_backend.md), [`modules/frontend.md`](../../knowledge/context/modules/frontend.md)

## Symptom (exact)

`npm run dev` browser calls fail; Vite terminal shows:

```text
[vite] http proxy error: /api/maintenance/...
AggregateError [ECONNREFUSED]
```

or Network tab shows `http://localhost:5173/api/...` proxied to `http://localhost:8000` with connection refused.

## Root cause (confirmed)

| Layer | Behavior |
| --- | --- |
| `frontend/src/api/client.js` | Axios `baseURL` defaults to `import.meta.env.VITE_API_URL` or `'/api'` |
| Vite | When `baseURL` is `/api`, requests stay same-origin and hit the **dev proxy** → `VITE_PROXY_TARGET` or `http://localhost:8000` |
| `.env.example` | **Not loaded by Vite** — documentation only |
| Missing `.env.development` / `.env.local` | Team silently aimed at localhost even though staging was live |

This is **not** a Neo4j or Groq failure. Staging can be healthy while local Vite still proxies to a dead `:8000`.

## Fix (versioned — automatic after pull)

Committed file: `frontend/.env.development`

```env
# Loaded automatically by Vite during `npm run dev`.
VITE_API_URL=https://dev1.corp.curatech.pk/halite-api/api
```

Also documented in `frontend/.env.example` (still not auto-loaded).

### Partner steps

1. `git pull` branch that contains `.env.development`  
2. **Stop** Vite completely  
3. `npm run dev` again (env files are read at process start only)  
4. Confirm Network tab host is `dev1.corp.curatech.pk`, not `localhost:8000`

## Optional local backend override

Create **gitignored** `frontend/.env.local` (overrides development):

```env
VITE_API_URL=/api
VITE_PROXY_TARGET=http://localhost:8000
```

Only use when running `uvicorn` locally. Do not commit `.env.local`.

## Proof checklist (agents)

| Check | How | Pass criteria |
| --- | --- | --- |
| File present | `frontend/.env.development` exists in git | Contains staging URL |
| Vite restarted | Kill + `npm run dev` after env change | Process started after file change |
| Network host | Browser DevTools → Network | Requests to `dev1.corp.curatech.pk` |
| Health | App or curl staging health | `graph_mode` / `llm_mode` visible |
| No secrets committed | `git status` | No `.env.local`, no OPS_TOKEN |

```powershell
# Staging reachable without Vite
Invoke-RestMethod https://dev1.corp.curatech.pk/halite-api/api/health | Select-Object status, graph_mode, llm_mode, git_sha
```

## Related failures (do not confuse)

| Symptom | Actual cause | Doc |
| --- | --- | --- |
| Pages hang 30–90s after staging works | Assets N+1 + history fan-out | [`10_perf_assets_api_handoff.md`](10_perf_assets_api_handoff.md) |
| Diagnose 503 | Groq not live | [`12`](12_u4_u5_diagnostics_handoff.md) |
| Diagnose 404 | Bad asset / no history | [`11`](11_u2_real_data_retrieval.md) |
| Occasional 502 from Caddy | Transient VM/container | Retry; check `/api/ops/version` |

## Agent anti-ambiguity

- Do **not** tell partners to “just set `.env.example`”.  
- Do **not** assume localhost `:8000` is staging.  
- Staging CD: [`remote_backend.md`](../../knowledge/context/modules/remote_backend.md).  
- Parent: [`08_umar_progress.md`](08_umar_progress.md).
