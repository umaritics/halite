---
id: mod-diagnostics
title: Diagnostics module
status: active
owners: [Umar]
updated: 2026-10-16
depends_on: [ctx-data-graph]
---

# Module: Diagnostics

## Purpose

Given `asset_id` + `symptom_text`, retrieve graph-backed historical context, produce a **deterministic initial ranking** of investigative checks, validate citations, and optionally ask the LLM to explain structured evidence (not invent procedures).

## Primary files

| File | Role |
| --- | --- |
| `backend/api/routes/diagnostics.py` | `POST /api/maintenance/diagnose`, `POST /api/maintenance/chat`; cache; citation validation; LLM gate |
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

## Ranking honesty (Mid-I)

- Current approach is **case-based / heuristic exploratory ranking**, not a trained predictive fault model.
- Conflict-detection F1 must **not** be reported as diagnostic accuracy.
- Scores are ranking aids, **not** calibrated probabilities.

## LLM boundary

- Live Groq required for fresh diagnose unless a valid diag cache hit exists.
- Missing live model → controlled **503** (or clear cache path), never silent fake diagnosis.
- Citations: only IDs present in retrieved context may be confirmed; fabricated IDs flagged/dropped.

## Contract freeze (diagnose)

Request: `{ "asset_id": "...", "symptom_text": "..." }`  
Response fields expected by UI (verify in code before renaming): `ranked_checks`, explanation, evidence/citations, citation validation status, warnings. Coordinate renames with Shahmeer.

## Related

- Flow: [FLOW-diagnose.md](../../flows/FLOW-diagnose.md)
- U1 audit (executed inventory): [diagnostics_u1_audit.md](diagnostics_u1_audit.md)
