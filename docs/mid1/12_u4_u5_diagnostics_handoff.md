# U4 / U5 — Citation boundary + diagnostic backend tests

Owner: Umar  
Branch: `umar/mid1-graph-diagnostics`  
Date: 2026-10-16

## U4 — Citation validation / LLM boundary

| Rule | Behavior |
| --- | --- |
| Live Groq required | Fresh `POST /diagnose` → **503** when `is_live=False` and no cache hit |
| Empty history | **404** (controlled) |
| Citations | `services/citation_validation.py` extracts FAA-shaped IDs (`SWIA…`, `AALA…`); graph miss → `[UNVERIFIED:ID]` |
| Invented IDs | Never accepted as `valid_ids`; `citation_validation.all_valid=false` |

## U5 — Backend tests (Shahmeer can rely on these)

| Test module | Covers |
| --- | --- |
| `backend/tests/test_citation_validation.py` | FAA ID extract + valid/invalid flagging |
| `backend/tests/test_api_diagnostics.py` | 503 / 404 / citation flagging / ranked_checks on diagnose |
| `backend/tests/test_diagnostic_retrieval.py` | Context build + U3 ranking |

Test app (`tests/conftest.py`) now registers the diagnostics router (same as `main.py`).

### Fixture pattern for UI wiring

Seed FAA-shaped `record_id`s (not `SEED001`) if you assert citation parsing. Example IDs used in tests: `SWIA2025091876593`, `AALA202504075792`.

### Response fields for Diagnostics UI

`ranked_checks[]`: `part_name`, `score`, `rank`, `evidence_record_ids`, `sources`, `evidence_count`  
Top-level: `explanation`, `evidence`, `citation_validation.{valid_ids,invalid_ids,all_valid}`, `context_size`, `warnings`

Do not rename without a DEC + Umar.

## Related

- Perf (assets N+1): `10_perf_assets_api_handoff.md` (Shahmeer + Usman)
- Staging retrieval proof: `11_u2_real_data_retrieval.md`
