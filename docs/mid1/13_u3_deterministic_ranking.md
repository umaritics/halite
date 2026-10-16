# U3 — Deterministic ranking and provenance

Owner: Umar  
Branch: `umar/mid1-graph-diagnostics`  
Date: 2026-10-16  
Code SHA: `e8093cb` (feature); tip includes later U4/U5 at `a70652e`  
Knowledge: [`diagnostics.md`](../../knowledge/context/modules/diagnostics.md), [`FLOW-diagnose.md`](../../knowledge/flows/FLOW-diagnose.md), [`diagnostics_u1_audit.md`](../../knowledge/context/modules/diagnostics_u1_audit.md)

## Goal

Make inspection ranking **repeatable**, **graph-only**, and **honestly labeled** (heuristic scores, not probabilities). LLM must not invent rank order.

## Problem found in U1

`_rank_components` in `diagnostics.py` sorted by `score` only. Equal scores could reorder across Python versions or dict iteration order → flaky demos and unstable UI.

## Solution

1. Move ranking to `services/diagnostic_retrieval.py` as `rank_diagnostic_checks`.  
2. Publish named weight constants.  
3. Stable sort key: `(-score, -evidence_count, part_name)`.  
4. Sort `evidence_record_ids` and `sources` for stable JSON.  
5. Skip blank / `UNKNOWN` part names (prevents empty top checks).

## Weight table (documented constants)

| Constant | Value | Meaning |
| --- | --- | --- |
| `RANK_WEIGHT_ASSET_HISTORY` | `0.4` | Multiplier on asset-history recency signal |
| `RANK_WEIGHT_FLEET_MATCH` | `0.6` | Multiplier on fleet similarity score |
| `RANK_SUPERSEDED_PENALTY` | `0.3` | Applied when `is_superseded` |

Asset-history contribution for index `i` (newest first):  
`(1/(i+1)) * superseded_penalty * RANK_WEIGHT_ASSET_HISTORY`

Fleet contribution:  
`fleet_score * superseded_penalty * RANK_WEIGHT_FLEET_MATCH`  
where `fleet_score` comes from Jaccard/JASC heuristic in `similar_symptom_records` (+0.50 JASC, +0.30 part Jaccard, +0.20 text Jaccard).

## `ranked_checks` item schema (frozen for Shahmeer)

| Field | Type | Notes |
| --- | --- | --- |
| `part_name` | string | Uppercased component key — **UI field name; not `component`** |
| `score` | float | Rounded to 4 decimals; **not** a calibrated probability |
| `evidence_count` | int | Distinct record IDs |
| `evidence_record_ids` | string[] | Sorted ascending |
| `sources` | string[] | Sorted; values include `asset_history`, `fleet_match` |
| `rank` | int | 1-based after stable sort |

Response caps list at 10 in `POST /diagnose`.

## Tests executed

```text
cd backend
python -m pytest -q tests/test_diagnostic_retrieval.py::TestRankDiagnosticChecks
```

| Test | Proves |
| --- | --- |
| `test_ranks_have_provenance` | every item has part_name, rank, evidence, sources; IDs sorted |
| `test_stable_tie_break_by_part_name` | equal fleet scores → ALPHA before ZEBRA |
| `test_deterministic_across_calls` | same context → identical order/scores |
| `test_skips_blank_part_names` | `""` / `UNKNOWN` dropped |

## Agent anti-ambiguity rules

- Do **not** rename `part_name` → `component` without a DEC and Shahmeer sync.  
- Do **not** call scores “confidence” or “probability” in UI copy.  
- Do **not** reintroduce LLM-based ranking.  
- Superseded evidence may appear but is down-weighted; UI should surface superseded status from evidence records when possible.

## Related

- Route: `backend/api/routes/diagnostics.py` calls `rank_diagnostic_checks(context)`.  
- Parent audit: [`08_umar_progress.md`](08_umar_progress.md).
