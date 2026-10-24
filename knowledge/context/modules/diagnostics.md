---
id: mod-diagnostics
title: Diagnostics module
status: active
owners: [Umar]
updated: 2026-10-17
depends_on: [ctx-data-graph]
---

# Module: Diagnostics

## Purpose

Given `asset_id` + `symptom_text`, retrieve graph-backed historical context, produce a **deterministic initial ranking** of investigative checks, validate citations, and optionally ask the LLM to explain structured evidence (not invent procedures).

## Primary files

| File | Role |
| --- | --- |
| `backend/api/routes/diagnostics.py` | One-shot diagnose, legacy chat, stateless copilot turn; cache; citation validation; LLM gate |
| `backend/services/diagnostic_retrieval.py` | History context, similar-symptom search, `build_diagnostic_context` |
| `backend/tests/test_diagnostic_retrieval.py` | Unit/integration tests Umar extends |
| `frontend/src/pages/Diagnostics.jsx` | Shahmeer UI consumer |

## Key functions (`diagnostic_retrieval.py`)

| Function | Behavior (label honestly) |
| --- | --- |
| `asset_history_context` | Recent records for an asset from graph |
| `similar_symptom_records` | Lexical / field overlap style similarity (not proven embedding index) |
| `resolution_outcomes` | Follow-on outcomes for candidate IDs |
| `build_diagnostic_context` | Assembles context for diagnose |
| `rank_diagnostic_checks` | Deterministic part ranking + stable tie-break (U3) |
| `build_copilot_context` | Accumulated symptoms + observations, optional aircraft scope, bounded fleet scan |
| `rank_copilot_checks` | Active evidence only; excludes explicitly ruled-out components |
| `ranking_delta` | Stable moved-up/down/new/dropped + newly retrieved evidence delta |

## Copilot contract

`POST /api/maintenance/copilot/turn` accepts
`{session_id?, asset_id?, message, case_state?}`. `asset_id` is optional; absent
means fleet-wide retrieval. The client carries state because the server is
stateless. The response includes `reply`, merged `case_state`, deterministic
`ranked_checks`, `ranking_delta`, evidence, citation validation, `llm_status`,
and warnings.

Case state has `symptoms`, `observations`, `checks_done`, `ruled_out`, and
`open_questions`. LLM extraction is strict JSON; invalid extraction retains the
raw message. Model failure returns HTTP 200 with `reply:null`, an unavailable
status, and deterministic evidence/ranking. Unknown aircraft is 404; blank or
oversized messages are 422.

`symptoms` and `observations` are intentionally distinct extraction fields. A
reported crack may therefore appear only as an observation while Symptoms is
empty; the frontend must not promote it automatically. Changing that taxonomy
belongs to the extraction contract, not presentation normalization.

Explicit record IDs and aircraft/date/topic report requests are selected
deterministically before the model summarizes them. Superseded records remain
visible evidence but are excluded from copilot recommendations.

When an aircraft is selected, fleet retrieval deliberately excludes that asset
and can return other-aircraft matches. Those records are ranking context, not a
claim about the selected aircraft; the frontend preserves them and labels their
provenance rather than filtering or reranking them.

## Ranking honesty (Mid-I)

- Current approach is **case-based / heuristic exploratory ranking**, not a trained predictive fault model.
- Conflict-detection F1 must **not** be reported as diagnostic accuracy.
- Scores are ranking aids, **not** calibrated probabilities.
- Weights: `RANK_WEIGHT_ASSET_HISTORY=0.4`, `RANK_WEIGHT_FLEET_MATCH=0.6`, `RANK_SUPERSEDED_PENALTY=0.3`.
- Tie-break: score DESC → evidence_count DESC → part_name ASC. Evidence IDs and sources sorted.

## LLM boundary

- `GroqService` rejects `None`/blank content. GPT-OSS uses low reasoning effort,
  excludes reasoning output, and has a larger completion budget. The default is
  consistently `openai/gpt-oss-20b` in config, wrapper, and `.env.example`.

- Live Groq required for fresh diagnose unless a valid diag cache hit exists.
- Missing live model → controlled **503** (or clear cache path), never silent fake diagnosis.
- Citations: `services/citation_validation.py` — FAA-shaped tokens verified against graph; fabricated IDs → `[UNVERIFIED:…]` and `citation_validation.invalid_ids`.
- Copilot applies a second current-turn boundary after graph verification: a real
  graph ID is also marked `[UNVERIFIED:…]` when it is absent from the returned
  `evidence[]`. `_collect_evidence` orders IDs from the top ten ranked checks and
  caps evidence at 20 records, while `RANKED_CHECKS` can still expose additional
  evidence IDs to the model. `valid_ids` therefore means “exists and was in this
  turn's bounded evidence,” not “supports every associated prose claim.” The API
  currently combines nonexistent and out-of-context IDs in `invalid_ids`.
- Tests: `test_citation_validation.py`, `test_api_diagnostics.py`. Handoff: [docs/mid1/12_u4_u5_diagnostics_handoff.md](../../../docs/mid1/12_u4_u5_diagnostics_handoff.md).

## Contract freeze (diagnose)

Request: `{ "asset_id": "...", "symptom_text": "..." }`  
Response fields expected by UI (verify in code before renaming): `ranked_checks`, explanation, evidence/citations, citation validation status, warnings. Coordinate renames with Shahmeer.

## U2 retrieval bounds (real Neo4j corpus)

- Asset window: `list_asset_history_recent` (DESC + LIMIT), default 30 for diagnose context.
- Fleet scan: `list_service_records(limit=FLEET_SCAN_CAP)` with `FLEET_SCAN_CAP=2500` in `diagnostic_retrieval.py`.
- Outcomes: batched `get_service_records_by_ids`.
- Controlled failures: unknown asset history → 404; diagnose with empty history → 404.
- Staging evidence: [docs/mid1/11_u2_real_data_retrieval.md](../../../docs/mid1/11_u2_real_data_retrieval.md).

## Related

- Flow: [FLOW-diagnose.md](../../flows/FLOW-diagnose.md)
- U1 audit (executed inventory): [diagnostics_u1_audit.md](diagnostics_u1_audit.md)
