# Frontend → shared staging API (Mid-I)

Owner note: Umar / team  
Date: 2026-10-16

## Symptom

`npm run dev` prints:

```text
[vite] http proxy error: /api/...
AggregateError [ECONNREFUSED]
```

## Cause

Axios defaults to `baseURL: '/api'`. Vite then proxies `/api` to **`http://localhost:8000`**.  
If no local backend is running, every request fails — even when staging is up.

`.env.example` alone is **not** loaded by Vite.

## Fix (versioned — partners get this automatically after pull)

Committed file:

`frontend/.env.development`

```env
VITE_API_URL=https://dev1.corp.curatech.pk/halite-api/api
```

Vite loads this in development mode. After `git pull`:

1. Stop the dev server  
2. `npm run dev` again (env files are read at startup)

No manual `.env.local` required for Mid-I team use of the shared backend.

## Optional local backend override

Create **gitignored** `frontend/.env.local`:

```env
VITE_API_URL=/api
VITE_PROXY_TARGET=http://localhost:8000
```

## Agent checklist

- [ ] Confirm `frontend/.env.development` exists and points at staging  
- [ ] Restart Vite after changing env files  
- [ ] Sanity: browser Network tab shows requests to `dev1.corp.curatech.pk`, not `localhost:8000`  
- [ ] Do not commit secrets or personal `.env.local`
