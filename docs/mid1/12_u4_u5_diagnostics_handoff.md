# U4 / U5 — Citation boundary, LLM gate, diagnose tests, UI handoff

Owner: Umar → Shahmeer (UI consumer)  
Branch: `umar/mid1-graph-diagnostics`  
Date: 2026-10-16  
Code SHA: `a70652e`  
Knowledge: [`diagnostics.md`](../../knowledge/context/modules/diagnostics.md), [`FLOW-diagnose.md`](../../knowledge/flows/FLOW-diagnose.md), [`modules/frontend.md`](../../knowledge/context/modules/frontend.md)

## Executive

| Package | Verdict |
| --- | --- |
| **U4** Citation validation + LLM boundary | **PASS** — module + unit + API tests; staging live cite-ok in U2 |
| **U5** Backend tests + UI contract handoff | **PASS** — diagnostics router in test app; field freeze below |

## U4 — Rules agents must not weaken

| Rule | Behavior | Proof |
| --- | --- | --- |
| Live Groq required for fresh diagnose | `is_live=False` and no cache → HTTP **503** | `test_api_diagnostics.py::test_503_when_llm_not_live` |
| Empty / missing history | HTTP **404** | `test_404_when_no_history` + staging U2 |
| Extract FAA-shaped IDs only | Regex `\b([A-Z]{2,6}\d{6,})\b` | `test_citation_validation.py` |
| Graph miss = invalid | `[UNVERIFIED:ID]` in explanation; `invalid_ids` populated | `test_flags_invented_ids_keeps_real` |
| Invented IDs never “valid” | `citation_validation.all_valid=false` if any invalid | same |
| Underscore / short demo IDs | `SEED001`, `R1_OLD` **not** extracted as citations | `test_ignores_short_or_underscore_ids` |

### Module

`backend/services/citation_validation.py`

- `extract_record_id_candidates(text)`  
- `validate_citations(text, graph_repo)` → `{valid, invalid, flagged_text}`  
- Batch lookup via `get_service_records_by_ids` when available  

Used by `POST /diagnose` and `POST /chat` in `backend/api/routes/diagnostics.py`.

### Real ID shapes (from staging corpus)

| Example | Notes |
| --- | --- |
| `SWIA2025091876593` | Observed on `813SK` history |
| `AALA202504075792` | Observed in diagnose evidence lists |

If FAA ever ships a new ID shape that fails the regex, **extend the regex + tests** — do not disable validation for demos.

### Cache note

Diagnose caches under `MAINT_DATA_DIR/diag_cache/cache.json` keyed by `(asset_id, normalised symptom, model)`. Cache hits can return without live Groq. Tests set `PYTEST_CURRENT_TEST` so cache is skipped. Agents debugging “stale diagnose” should clear cache or change symptom/model.

## U5 — Tests agents can re-run

```text
cd backend
set DEMO_MODE=true
set NEO4J_URI=
set NEO4J_PASSWORD=
set GROQ_API_KEY=
python -m pytest -q tests/test_citation_validation.py tests/test_api_diagnostics.py tests/test_diagnostic_retrieval.py
→ 35 passed (2026-10-16, Windows Python 3.12)
```

| Module | Covers |
| --- | --- |
| `tests/test_citation_validation.py` | Extract, dedupe, valid/invalid flagging |
| `tests/test_api_diagnostics.py` | 503, 404, invented-ID flagging, all_valid path, ranked_checks present |
| `tests/test_diagnostic_retrieval.py` | Context, fleet exclude, U3 ranking |

**Test app change:** `tests/conftest.py` `_build_test_app()` now `include_router(diagnostics_router)` — same as `main.py`. Without this, diagnose routes were invisible to TestClient.

### Fixture pattern (critical for Shahmeer / future tests)

Seed **FAA-shaped** `record_id`s if you assert citation parsing:

```text
SWIA2025091876593
AALA202504075792
```

Do **not** expect `SEED001` to appear in `citation_validation` — the regex intentionally excludes it.

## Diagnose response contract (frozen)

`POST /api/maintenance/diagnose`  
Request: `{ "asset_id": "<uuid>", "symptom_text": "<text>" }`

| Field | Type | UI guidance |
| --- | --- | --- |
| `ranked_checks` | array (≤10) | Primary list; use **`part_name`**, `rank`, `score`, `evidence_record_ids`, `sources`, `evidence_count` |
| `explanation` | string | May contain `[UNVERIFIED:…]` — show warning style |
| `evidence` | array | Cited valid records (subset) |
| `rare_cases` | array | Only graph-verified rare IDs |
| `citation_validation.valid_ids` | string[] | |
| `citation_validation.invalid_ids` | string[] | Show if non-empty |
| `citation_validation.all_valid` | bool | Gate “citations trusted” badge |
| `context_size` | object | Includes `asset_records`, `fleet_records`, `fleet_assets`, `wall_clock_s` |
| `warnings` | string[] | From LLM JSON if present |

**Rename policy:** any field rename requires a `knowledge/decisions/DEC-*` and Shahmeer update. See [`AGENTS.md`](../../AGENTS.md).

### HTTP statuses UI must handle

| Status | Meaning | UI |
| --- | --- | --- |
| 200 | OK | Render ranked_checks + citation panel |
| 404 | No history / bad asset | Honest empty state (“no history for this asset”) |
| 503 | Groq not live / not configured | Fail loud — do not invent a diagnosis |
| 422 | Validation | Show field errors |
| slow 200 (~15–60s) | Groq + Aura | Loading spinner; do not timeout at 5s |

## Shahmeer wiring checklist

- [ ] `maintenanceAPI.diagnose(assetId, symptomText)` against staging (`09`)  
- [ ] Loading state for long diagnose  
- [ ] Display `part_name` (not `component`)  
- [ ] Click-through `evidence_record_ids` → record/history  
- [ ] Surface `citation_validation.invalid_ids` / UNVERIFIED markers  
- [ ] 503 and 404 copy  
- [ ] Do not call `GET /assets` in a loop that also pulls all histories (see [`10`](10_perf_assets_api_handoff.md))  
- [ ] Frontend CI `getRecord` mock ([`06`](06_frontend_review_queue_handoff.md))

## Problems / anti-patterns

| Anti-pattern | Why wrong | Do instead |
| --- | --- | --- |
| Disable citation check for demo | Invented IDs look real | Keep validation; fix LLM prompt / grounding |
| Treat `score` as % confidence | Uncalibrated heuristic | Label “rank score” / “priority” |
| Use `SEED001` in citation tests | Regex ignores it | Use SWIA/AALA shapes |
| Point UI at localhost without backend | ECONNREFUSED | [`09`](09_frontend_shared_api.md) |
| Cache Redis for Mid-I diagnose | Wrong bottleneck | Fix N+1 assets; Groq latency is separate |

## Related

- Staging live proof: [`11_u2_real_data_retrieval.md`](11_u2_real_data_retrieval.md)  
- Ranking: [`13_u3_deterministic_ranking.md`](13_u3_deterministic_ranking.md)  
- Parent audit: [`08_umar_progress.md`](08_umar_progress.md)
