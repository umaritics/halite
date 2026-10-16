# U2 — Real-data graph retrieval (staging + Neo4j proof)

Owner: Umar  
Branch: `umar/mid1-graph-diagnostics`  
Date: 2026-10-16  
Staging tip observed during proof: `0f471b5` (health `git_sha`); bound-query code landed in `408d1c4`  
Knowledge: [`diagnostics.md`](../../knowledge/context/modules/diagnostics.md), [`04_data_and_graph.md`](../../knowledge/context/04_data_and_graph.md), [`FLOW-diagnose.md`](../../knowledge/flows/FLOW-diagnose.md), [`remote_backend.md`](../../knowledge/context/modules/remote_backend.md)

## Goal

Prove diagnose/history against the **live FAA corpus in Neo4j/Aura** (via shared staging), with **bounded** graph reads and **controlled** empty/unknown failures. Retrieval remains graph-grounded — **not Redis**, not embeddings.

## Verification standard

| Mark | Meaning |
| --- | --- |
| **PASS** | Executed command or inspectable query result recorded here |
| **CODE** | Behavior implemented and covered by unit tests |
| **HANDOFF** | Owned by another partner; not claimed done |

## Corpus proof (Neo4j MCP / Aura — same DB staging uses)

Executed 2026-10-16 via Neo4j read-cypher:

```cypher
MATCH (a:Asset)
OPTIONAL MATCH (sr:ServiceRecord)-[:ABOUT]->(a)
WITH a, count(sr) AS n
RETURN count(a) AS assets, sum(n) AS total_links, max(n) AS max_history

MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset)
WITH a.id AS asset_id, a.tail_number AS tail, count(sr) AS n
RETURN asset_id, tail, n ORDER BY n DESC LIMIT 10
```

| Metric | Value |
| --- | --- |
| Assets | **118** |
| ServiceRecord→Asset links | **2078** (health may report **2079** after ops/keepalive edges — use health as API truth) |
| Densest asset | tail **`813SK`**, **153** records |
| Asset UUID | `aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb` |
| Sample newest IDs | `SWIA2025122876590` (DRAG ANGLE), … |

Top densest tails (for demos): `813SK` (153), `508AE` (118), `860NW` (113), `173US` (71), …

This **closes the gap** Usman marked A1.3 as “file only”: the same 118 / 2079 / 813SK facts now hold in the running graph.

## Staging API proof (laptop → VM → Aura)

Base: `https://dev1.corp.curatech.pk/halite-api/api`  
Method: PowerShell `Invoke-RestMethod` / `Stopwatch` (2026-10-16). Brief 502 observed once during probe; retried successfully.

| ID | Request | HTTP | Timing | Observed | Status |
| --- | --- | --- | --- | --- | --- |
| U2.H | `GET /health` | 200 | ~3.1s | `graph_mode=neo4j`, `llm_mode=live`, `maintenance_record_count=2079`, `git_sha=0f471b5…` | PASS |
| U2.Hist | `GET /maintenance/assets/aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb/history` | 200 | ~0.99s | `count=153`; first record `SWIA2025091876593` / ROLLER (ascending history) | PASS |
| U2.Unk | `GET /maintenance/assets/not-a-real-asset/history` | **404** | ~0.73s | Controlled unknown asset | PASS |
| U2.Diag | `POST /maintenance/diagnose` body `{asset_id: 813SK UUID, symptom_text: "pump leak hydraulic"}` | 200 | ~15.96s | `ranked_checks=10`, `context_size.asset_records=30`, `fleet_records=20`, `citation_validation.all_valid=true`, `wall_clock_s≈15.57` | PASS |
| U2.Empty | `POST /diagnose` asset `00000000-0000-0000-0000-000000000000` | **404** | ~4.4s | Empty/missing history controlled | PASS |

### Sanitized diagnose proof (no explanation text / no secrets)

```json
{
  "http": 200,
  "asset_id": "aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb",
  "symptom_text": "pump leak hydraulic",
  "ranked_checks_count": 10,
  "context_size": { "asset_records": 30, "fleet_records": 20 },
  "citation_validation": { "all_valid": true },
  "wall_clock_s": 15.57,
  "note": "Use field part_name on ranked_checks; component is not a response key"
}
```

## Code bounds implemented (U2)

Files: `backend/graph/queries.py`, `memory_store.py`, `services/diagnostic_retrieval.py`

| Path | Before (U1 risk) | After |
| --- | --- | --- |
| Asset window for diagnose | `list_asset_history(limit=200)` then truncate to 30 | `list_asset_history_recent` — Cypher `ORDER BY occurred_at DESC LIMIT` |
| Fleet scan | `list_service_records()` unbounded | `list_service_records(limit=FLEET_SCAN_CAP)` with `FLEET_SCAN_CAP=2500` |
| Resolution outcomes | N× `get_service_record` | Batch `get_service_records_by_ids` |

Unit coverage: `test_graph_maintenance.py::test_recent_newest_first_and_limited`, `test_diagnostic_retrieval.py::test_unknown_asset_returns_empty`.

### Honest limits (do not overclaim)

- Fleet scoring is still **lexical Jaccard** over up to 2500 newest records — fine for Mid-I ~2k, **not** a vector index.  
- Diagnose ~16s is dominated by **Groq + context assembly**, not missing Redis.  
- `GET /maintenance/assets` list remains slow (N+1) — **not U2**; see [`10_perf_assets_api_handoff.md`](10_perf_assets_api_handoff.md).

## Controlled failure matrix (agents)

| Condition | Endpoint | Expected |
| --- | --- | --- |
| Unknown asset id | `GET .../history` | **404** `Asset … not found` |
| Known asset, zero history | `GET .../history` | 200 with `count=0` (if asset exists) |
| No / empty history for diagnose | `POST .../diagnose` | **404** no history |
| LLM not live, no cache | `POST .../diagnose` | **503** (U4; tested locally) |

## Problems / ambiguities resolved for agents

| Ambiguity | Clarification |
| --- | --- |
| Demo asset hardcode | Prefer `813SK` UUID above; always re-check health/history if corpus reloaded |
| “Redis will fix diagnose latency” | False for Mid-I; see timing split above |
| Usman A1 blocked forever | File facts now match running Neo4j on staging; Usman should update A1 evidence |
| History order | Public history API is **ascending** by `occurred_at`; diagnose context uses **newest-first** window of 30 |

## Re-run commands

```powershell
$base = "https://dev1.corp.curatech.pk/halite-api/api"
Invoke-RestMethod "$base/health" | Select-Object graph_mode, llm_mode, maintenance_record_count, git_sha
$aid = "aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb"
(Invoke-RestMethod "$base/maintenance/assets/$aid/history").count
$body = @{ asset_id = $aid; symptom_text = "pump leak hydraulic" } | ConvertTo-Json
# Long timeout — Groq
Invoke-RestMethod -Method POST -Uri "$base/maintenance/diagnose" -ContentType "application/json" -Body $body -TimeoutSec 180 |
  Select-Object @{n='ranked';e={$_.ranked_checks.Count}}, @{n='cite';e={$_.citation_validation.all_valid}}
```

## Out of scope

| Item | Owner | Doc |
| --- | --- | --- |
| Assets list N+1 | Usman + Shahmeer | [`10`](10_perf_assets_api_handoff.md) |
| Rank tie-break | Umar U3 | [`13`](13_u3_deterministic_ranking.md) |
| Citation regex depth | Umar U4 | [`12`](12_u4_u5_diagnostics_handoff.md) |

## Related

- Parent audit: [`08_umar_progress.md`](08_umar_progress.md)  
- Usman prior A1 file facts: [`05_usman_final_audit.md`](05_usman_final_audit.md) §A1.3
