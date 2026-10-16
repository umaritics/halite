# Mid-I performance handoff — slow frontend loads

Owner for fix: **Shahmeer** (frontend load patterns) + **Usman** (maintenance list APIs)  
Diagnosed by: Umar  
Date: 2026-10-16  
Status: **backend fix implemented on integration branch; staging timing pending**<br>
Knowledge: [`remote_backend.md`](../../knowledge/context/modules/remote_backend.md), [`modules/frontend.md`](../../knowledge/context/modules/frontend.md), Usman maintenance ownership in [`02_ownership_mid1.md`](../../knowledge/context/02_ownership_mid1.md)

## Verdict for agents

| Question | Answer |
| --- | --- |
| Is Redis required for Mid-I? | **No** |
| Primary bottleneck? | **Backend N+1** on `GET /api/maintenance/assets` |
| Secondary bottleneck? | **Frontend fan-out** of all asset histories on Service Records |
| Diagnose ~16s? | Mostly **Groq + retrieval**, separate from assets list; see [`11`](11_u2_real_data_retrieval.md) |

## Symptom

With frontend correctly pointed at staging ([`09`](09_frontend_shared_api.md)), Assets / Service Records / Diagnostics dropdowns feel broken (tens of seconds to minutes). Local `ECONNREFUSED` is a different bug.

## Timed staging endpoints (laptop → VM → Aura)

Order of magnitude from 2026-10-16 probes (exact ms vary with Aura):

| Endpoint | Approx | Severity |
| --- | --- | --- |
| `GET /api/health` | ~3–4 s | Acceptable cold |
| `GET /api/domains` | ~0.6 s | OK |
| `GET /api/alerts` | ~1 s | OK |
| `GET /api/maintenance/assets` | **~30–90s+** | **Primary** |
| `GET /api/maintenance/assets/{id}/history` (single) | ~1 s for 153 rows | OK when called once |
| `GET /api/maintenance/review-queue` | depends on queue | Usually OK |
| `POST /api/maintenance/diagnose` | ~15–20 s | Groq-bound; not this handoff |

## Root cause 1 — Backend N+1 (Usman-owned)

File: `backend/api/routes/maintenance.py` → `list_assets`

For **each** of ~118 assets:

```python
count = len(graph_repo.list_asset_history(asset["id"], limit=9999))
```

≈ 118 Neo4j round-trips; each materializes up to 9999 full `ServiceRecord` nodes **only to count**. With 2079 corpus rows over Aura RTT, this is catastrophic.

### Implemented fix (Usman)

One aggregation query, e.g.:

```cypher
MATCH (a:Asset)
OPTIONAL MATCH (sr:ServiceRecord)-[:ABOUT]->(a)
RETURN a, count(sr) AS record_count
ORDER BY a.tail_number
```

`GraphRepository.list_assets_with_counts()` now performs the aggregation in one
Neo4j query. `MemoryGraphStore.list_assets_with_counts()` provides the same
contract with one pass over `ABOUT` edges. The route no longer calls
`list_asset_history` inside a Python loop.

Regression coverage:

- `test_assets_listed_after_seed` fails if the route calls per-asset history.
- `TestListAssetsWithCounts` checks sorting, populated counts, and zero counts.
- Full backend result on the integration worktree: **122 passed, 18 skipped**.

### Acceptance

| Metric | Target |
| --- | --- |
| Staging `GET /api/maintenance/assets` | **&lt; 2–3 s** with ~2k records |
| Neo4j queries per request | **1** (or small constant) |

## Root cause 2 — Frontend history fan-out (Shahmeer-owned)

File: `frontend/src/pages/ServiceRecords.jsx` (pattern as of Mid-I)

On mount:

1. `maintenanceAPI.assets()` (already slow)  
2. `Promise.all(assets.map(a => maintenanceAPI.assetHistory(a.id)))` → **~118** history calls × up to 200 records

Even after assets is fixed, this page remains unusable until redesigned.

### Proposed fix (Shahmeer ± Usman)

**Preferred A:** selected-asset history only (same UX as Assets → detail).  
**Preferred B:** Usman adds `GET /api/maintenance/service-records?limit=&offset=&status=` and UI pages that.

Acceptance: Service Records initial load ≤ **2** API calls.

## Root cause 3 — Environment amplifier

Staging = VM + Aura. Each chatty call costs ~0.5–3 s RTT. Designs that feel fine on localhost MemoryGraph fail on staging. Optimize **query shape**, not cache layer first.

## Root cause 4 — App shell noise (minor)

`App.jsx` alerts polling; `DomainContext` domains fetch. Small vs assets. Avoid loading software `graph/overview` on maintenance Mid-I paths.

## Why not Redis first

| Argument | Response |
| --- | --- |
| “Cache assets for 60s” | Caches a **wrong** expensive computation; still N+1 on miss |
| “Cache history pages” | Does not fix 118 parallel first loads |
| Mid-I rubric | Needs correct APIs + honest latency, not infra sprawl |
| FYP-II | Redis/CDN optional after correct queries |

## Ownership split

| Work | Owner | Acceptance |
| --- | --- | --- |
| Aggregated assets Cypher | **Usman** | assets &lt; 2–3 s on staging |
| Stop all-history fan-out | **Shahmeer** | ≤ 2 calls on Service Records load |
| Diagnostics dropdown uses slim assets | **Shahmeer** | Usable without multi-minute wait |
| Optional slim JSON fields | Usman | Smaller payloads |

## Out of scope

- Redis / CDN / Cloudflare  
- Conflict engine changes  
- Diagnostic ranking / citation (Umar U2–U5 — already done)

## Agent checklist before “optimizing”

1. Confirm frontend hits staging ([`09`](09_frontend_shared_api.md)).  
2. Time `GET /maintenance/assets` alone vs full page.  
3. If assets alone is ~30s+, fix Usman N+1 first.  
4. If assets is fast but Service Records still slow, fix Shahmeer fan-out.  
5. Do not open a Redis ticket for Mid-I.

The code/query-count portion is complete. The latency target remains pending
until the integration SHA is deployed and timed against staging Aura.

## Related

- Umar audit: [`08_umar_progress.md`](08_umar_progress.md)  
- Staging guide: [`09_frontend_shared_api.md`](09_frontend_shared_api.md)  
- Diagnose latency context: [`11_u2_real_data_retrieval.md`](11_u2_real_data_retrieval.md)
