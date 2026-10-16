# Mid-I performance handoff — slow frontend loads

Owner for fix: **Shahmeer** (frontend load patterns) + **Usman** (maintenance list APIs)  
Diagnosed by: Umar  
Date: 2026-10-16  
Status: diagnosis only — **do not treat Redis as the first fix**

## Symptom

With frontend pointed at shared staging (`VITE_API_URL=…/halite-api/api`), pages feel very slow / sometimes hang. Local Vite proxy errors are unrelated; this is **API work + round-trips** against Neo4j/Aura over the internet.

## Timed staging endpoints (from laptop → VM)

| Endpoint | Approx | Notes |
| --- | --- | --- |
| `GET /api/health` | ~3–4 s | Cold/TLS + Aura health work; acceptable for occasional call |
| `GET /api/domains` | ~0.6 s | Fine |
| `GET /api/alerts` | ~1 s | Fine |
| `GET /api/maintenance/assets` | **tens of seconds** (often ~30–90s+) | **Primary bottleneck** |
| `GET /api/maintenance/review-queue` | depends on queue size | Usually smaller than assets |
| `GET /api/graph/overview` | can be large | Legacy software graph; Mid-I should avoid on critical path |

Exact numbers vary with Aura latency; order of magnitude is what matters.

## Root causes (confirmed in code)

### 1. Backend N+1 on `GET /api/maintenance/assets` (Usman-owned route)

File: `backend/api/routes/maintenance.py` → `list_assets`

For **every** asset (~118), the handler does:

```python
count = len(graph_repo.list_asset_history(asset["id"], limit=9999))
```

That means ~118 Neo4j queries, each returning up to 9999 full `ServiceRecord` nodes, just to compute a count. With 2079 corpus records this is catastrophic over Aura.

**Correct shape:** one Cypher aggregation, e.g.

```cypher
MATCH (a:Asset)
OPTIONAL MATCH (sr:ServiceRecord)-[:ABOUT]->(a)
RETURN a, count(sr) AS record_count
ORDER BY a.tail_number
```

No Redis required for this.

### 2. Frontend fan-out on Service Records page (Shahmeer-owned)

File: `frontend/src/pages/ServiceRecords.jsx`

On mount:

1. `maintenanceAPI.assets()` (already slow — see above)
2. Then `Promise.all(assets.map(a => maintenanceAPI.assetHistory(a.id)))`  
   → **~118 more history requests** (each up to 200 records)

So one page load can mean **1 + 118** heavy API calls. That will feel broken on staging even after assets is fixed, until this page is redesigned.

**Correct shape (frontend):**

- Do **not** load all fleet history client-side.
- Prefer a single paginated list endpoint (Usman adds `GET /api/maintenance/service-records?limit=&offset=&status=`) **or**
- Load history only for the selected asset (same pattern as Assets → AssetHistory).

### 3. Latency amplifier (environment, not a new product)

Staging is VM + Aura (remote). Each chatty request costs ~0.5–3 s RTT. Chatty designs that are “ok” on localhost become unusable. Optimization priority: **fewer/heavier-correct queries**, not Redis first.

### 4. App shell noise (Shahmeer)

`App.jsx` polls/fetches alerts; `DomainContext` loads domains on every app load. Those are minor vs assets/history, but Mid-I UI should avoid loading software-domain graph overview on maintenance paths.

## Is Redis needed?

**Not for Mid-I.** Redis helps cache repeated identical reads under load, but:

- Current slowness is **algorithmic N+1**, not missing a cache layer.
- Caching a wrong/slow assets response would still be wrong architecture.
- After a single aggregated Cypher + paginated records API, Redis is optional later (FYP-II SaaS), not a Mid-I gate.

## Proposed ownership split

| Work | Owner | Acceptance |
| --- | --- | --- |
| Replace assets count loop with one Cypher `count(sr)` query | **Usman** | `GET /assets` returns in **&lt; 2–3 s** on staging with 2k records |
| Stop ServiceRecords from fetching all histories; use paginated API or selected-asset history | **Shahmeer** (+ Usman if new list endpoint) | Service Records page does **≤ 2** API calls on load |
| Keep Diagnostics/Assets using slim assets list (id, tail, count only) | **Shahmeer** | Diagnostics asset dropdown usable without multi-minute wait |
| Optional: slim JSON (omit huge unused fields) | Usman | Response size reasonable |

## Out of scope for this handoff

- Redis / CDN / Cloudflare  
- Rebuilding conflict engine  
- Diagnostic ranking changes (Umar U2–U5)

## Related

- Staging guide: `docs/mid1/09_frontend_shared_api.md`  
- Umar progress: `docs/mid1/08_umar_progress.md`  
- Remote backend: `knowledge/context/modules/remote_backend.md`
