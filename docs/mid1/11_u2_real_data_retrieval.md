# U2 — Real-data graph retrieval (staging proof)

Owner: Umar  
Branch: `umar/mid1-graph-diagnostics`  
Date: 2026-10-16  
Staging SHA at proof: `0f471b5` (pre-bound deploy); bound-query code follows on this branch.

## Goal

Prove diagnose/history against the live Neo4j FAA corpus with **bounded** graph reads and **controlled** empty/unknown paths. No Redis; retrieval stays graph-grounded.

## Corpus (Neo4j / staging)

| Metric | Value |
| --- | --- |
| Assets | 118 |
| ServiceRecord→Asset links | ~2078–2079 |
| Densest demo asset | tail `813SK` (153 records), UUID `aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb` |

## Staging API proof (2026-10-16)

Base: `https://dev1.corp.curatech.pk/halite-api/api`

| Check | Result | Notes |
| --- | --- | --- |
| `GET /health` | 200 | `graph_mode=neo4j`, `llm_mode=live`, corpus 2079 |
| `GET .../assets/{813SK}/history` | 200, count=153 | ~1.0s |
| `GET .../assets/not-a-real-asset/history` | **404** | Unknown asset controlled |
| `POST .../diagnose` (813SK, “pump leak hydraulic”) | 200 | ~16s wall; `context_size` asset=30 fleet=20; `citation_validation.all_valid=true`; 10 ranked_checks |
| `POST .../diagnose` (nil UUID) | **404** | Empty/missing history controlled |

## Code bounds (this package)

| Path | Bound |
| --- | --- |
| Asset history for diagnose | `list_asset_history_recent` — Cypher `ORDER BY occurred_at DESC LIMIT` (default window 30) |
| Fleet similar-symptom scan | `list_service_records(limit=FLEET_SCAN_CAP)` with `FLEET_SCAN_CAP=2500` |
| Resolution outcomes | Batch `get_service_records_by_ids` (no per-id round trip) |

Honest limit: fleet scoring is still lexical over up to 2500 newest records (fine for Mid-I ~2k). Not an embedding index.

## Out of scope (not U2)

- Assets list N+1 / Redis → Shahmeer + Usman (`10_perf_assets_api_handoff.md`)
- Stable rank tie-break → **U3**
- Citation regex / 503 LLM boundary depth → **U4**
- Broader route test fixtures → **U5**

## Partner notes

- Prefer `813SK` for demos; confirm via health/history if corpus reloaded.
- Diagnose latency ~15–20s is mostly Groq + full context build, not Redis absence.
