---
id: mod-diagnostics-u1
title: U1 audit — diagnostic implementation state
status: active
owners: [Umar]
updated: 2026-10-16
work_package: U1
branch: umar/mid1-graph-diagnostics
baseline_sha: b949de4
tip_note: U2–U5 closed 2026-10-16; see docs/mid1/08_umar_progress.md
---

# U1 — Technical state note (diagnostics)

Acceptance target: inventory of executed functions, real retrieval/ranking methods, schema of `ranked_checks`, and explicit labels of what is **not** hybrid semantic retrieval. Conflict F1 is **not** diagnostic accuracy.

## Test baseline (executed)

```text
cd backend
DEMO_MODE=true NEO4J_URI= NEO4J_PASSWORD= GROQ_API_KEY=
python -m pytest -q tests/test_diagnostic_retrieval.py
→ 20 passed in 0.34s
```

These tests use `MemoryGraphStore` only (no live Neo4j, no Groq). Route-level diagnose tests and live Neo4j proof were completed in **U2/U5** (`docs/mid1/11_*.md`, `12_*.md`).

## Function inventory

### `backend/services/diagnostic_retrieval.py`

| Function | Inputs | Outputs | Notes |
| --- | --- | --- | --- |
| `_normalise` | string | uppercased collapsed whitespace | helper |
| `_text_similarity` | two strings | Jaccard on word sets ∈ [0,1] | **lexical**, not embeddings |
| `_record_is_superseded` | record dict | bool (`status == superseded`) | |
| `asset_history_context` | `graph_repo`, `asset_id`, `limit=30`, `exclude_synthetic` | list of history dicts newest-first | **U2:** `list_asset_history_recent` DESC LIMIT; drops `DEMO*` when exclude_synthetic |
| `similar_symptom_records` | symptom, optional JASC, exclude asset, limit | scored fleet records | **U2:** `list_service_records(limit=FLEET_SCAN_CAP)` then lexical score in Python |
| `resolution_outcomes` | list of record_ids | outcome dicts | **U2:** batch `get_service_records_by_ids`; marks superseded |
| `build_diagnostic_context` | asset_id, symptom | `{asset_history, fleet_matches, resolution_outcomes, context_size}` | Infers JASC hint from history part-name similarity > 0.2 |
| `rank_diagnostic_checks` | context dict | ranked part list | **U3:** stable tie-break; see `docs/mid1/13_u3_*.md` |

### `backend/api/routes/diagnostics.py` + `services/citation_validation.py`

| Function / route | Role |
| --- | --- |
| `_cache_key` / `_load_cache` / `_save_cache` | Diag response cache under `MAINT_DATA_DIR/diag_cache/cache.json` |
| `validate_citations` | **U4:** FAA-shaped extract → graph verify; invalid → `[UNVERIFIED:…]` |
| `rank_diagnostic_checks` | Imported from retrieval (no longer private `_rank_components`) |
| `_build_prompt` | Packs top ranked + sample history/fleet into LLM JSON instructions |
| `POST /diagnose` | Cache → live LLM gate → context → rank → LLM explain → cite validate → response |
| `POST /chat` | Grounded chat path (same module; see source for details) |

## Graph query paths (real)

| Need | Path |
| --- | --- |
| Asset history | `GraphRepository.list_asset_history(asset_id)` ← Neo4j `ServiceRecord-[:ABOUT]->Asset` (or memory equivalent) |
| Fleet scan | `GraphRepository.list_service_records()` then filter/score in Python (**not** a vector index query) |
| Citation check | `GraphRepository.get_service_record(record_id)` |

There is **no** embedding index, ANN search, or hybrid BM25+vector path in this code.

## Ranking method (honest label)

**Implemented:** deterministic, graph-derived **component (`part_name`) ranking**:

1. Asset history: weight `1/(rank_index+1) * superseded_penalty * 0.4` where superseded_penalty is 0.3 if superseded else 1.0.
2. Fleet matches: `fleet_similarity_score * superseded_penalty * 0.6`.
3. Sort by cumulative score descending; assign `rank`.

Fleet similarity itself: `+0.50` exact JASC, `+0.30 * Jaccard(symptom, part_name)`, `+0.20 * Jaccard(symptom, text)`.

**Not implemented:** trained fault classifier, calibrated probabilities, embedding retrieval, hybrid semantic-vector fusion.

LLM is used **only** to phrase `explanation` / `rare_cases` / `warnings` JSON after ranking exists. Ranking does not come from the LLM.

## `ranked_checks` item schema (as returned)

Each element of `ranked_checks` (capped to 10 in response):

| Field | Type | Meaning |
| --- | --- | --- |
| `part_name` | str | Uppercased component key |
| `score` | float | Uncalibrated ranking score (not a probability) |
| `evidence_count` | int | Distinct evidence record IDs |
| `evidence_record_ids` | list[str] | Provenance IDs |
| `sources` | list[str] | e.g. `asset_history`, `fleet_match` |
| `rank` | int | 1-based order |

Full diagnose response also includes: `evidence`, `rare_cases`, `explanation` (citation-flagged), `context_size` (+ `wall_clock_s`), `citation_validation.{valid_ids,invalid_ids,all_valid}`, `warnings`.

## Caveats (post U2–U5)

1. **Fleet scan:** still lexical over ≤2500 newest records — fine for Mid-I ~2k; **not** a vector architecture (bounded in U2).
2. **Empty history:** diagnose returns **404** — UI copy still Shahmeer (`docs/mid1/12_*`).
3. **Citation regex:** covered for `SWIA…` / `AALA…` in U4; extend + test if new FAA shapes appear.
4. **Tie-breaking:** U3 stable sort landed (`docs/mid1/13_*`).
5. **Demo IDs:** `exclude_synthetic` drops `DEMO*`; citation regex ignores `SEED001`-style IDs.
6. **Do not claim** conflict-detection precision/recall as diagnostic accuracy.
7. **Assets list N+1:** still open for Usman/Shahmeer (`docs/mid1/10_*`) — not a diagnostics ranking issue.

## Related docs

- Module hub: [diagnostics.md](diagnostics.md)
- Flow: [FLOW-diagnose.md](../../flows/FLOW-diagnose.md)
- Ownership: [02_ownership_mid1.md](../02_ownership_mid1.md)
