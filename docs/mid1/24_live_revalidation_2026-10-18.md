# Live re-validation on the real local stack — 2026-10-18

Owner: Shahmeer Atif · Scope: local stack only. **Shared staging was not called.**

## What was checked and where

| Item | Value |
| --- | --- |
| Code | `main` at `36a98a3` plus the fix in this change |
| Graph | Local Neo4j with the full corpus; `/api/health`: `graph_mode=neo4j`, `demo_mode=false`, 2,079 records |
| Model | `llm_mode=live`, `openai/gpt-oss-120b` (the local key). Staging uses `openai/gpt-oss-20b` |
| Aircraft | 813SK (153 records), asset UUID `92bdb741-…` on this graph |
| Method | HTTP calls to the running API; no mocks. Accept and reject were not used |

## Defect found: one-shot diagnosis was broken on `main`

The first live `POST /api/maintenance/diagnose` returned **HTTP 503**:
`Groq API error: Error code: 400 … 'messages.1.content' … Value is not nullable`.

- **Cause.** `_build_prompt` in `backend/api/routes/diagnostics.py` returned `None`. Its body stopped
  after building the ranked list; the fleet and history sections and the whole `return` were gone, so the
  route sent the model an empty user message.
- **Introduced by** commit `0968651` ("add stateless copilot turns", PR #5, merged 16 Oct). The function was
  intact at `c8f1712` and truncated from `0968651` onward, including the evaluated commit `36a98a3`.
- **Why CI passed.** The existing diagnose tests use a fake model whose `chat()` ignores its arguments, and
  the live-model path is never exercised in CI.
- **Impact.** Any *fresh* one-shot diagnosis on a live model fails with 503. Cached answers and the Copilot
  (which builds its own prompts) are unaffected. Shared staging reports `git_sha=36a98a3…` (public
  `/api/ops/version`), so it carries the same defect; this was **not** re-tested there.
- **Fix.** Restored the function body from `a70652e`, unchanged. Two regression tests (`test_diagnose_prompt.py`)
  inspect what the model is actually sent; both **fail on the broken version and pass on the fix**.

## Results after the fix

| Check | Result |
| --- | --- |
| `GET /api/health` | `neo4j`, `live`, `openai/gpt-oss-120b`, 2,079 records |
| Assets | 118 aircraft; largest 813SK (153), 508AE (118), 860NW (113) |
| History for 813SK (by UUID) | 153 records, oldest first, first `SWIA2025091876515` (2025-09-18) |
| Unknown aircraft | HTTP 404, ``Asset 'ZZ999' not found``; a tail number instead of the UUID also 404 |
| **Quick diagnose**, 813SK, "crack found on drag angle during inspection" | **HTTP 200 in 1.8 s of retrieval**; ranked DRAG ANGLE (1.4784), ANGLE (0.5888), FRAME (0.2), STRINGER (0.1921); explanation 1,045 characters; **13 cited record IDs valid, 0 invalid**; 10 evidence records |
| Context | 30 records on the aircraft, 20 fleet matches across 9 aircraft |
| **Copilot**, turn 1 | HTTP 200, `llm_status=available`, reply 2,855 characters, same top components |
| Copilot, turn 2 ("frame has been ruled out") | `ruled_out=['frame']`; FRAME no longer recommended; ranking delta reported (14 moved up, 1 dropped) |
| Copilot, a message naming `FAKE2025999999999` | HTTP 200; `FAKE2025999999999` listed in `invalid_ids` (also four real-looking IDs outside the retrieved context) |
| Copilot, unknown aircraft / blank message | 404 / 422 |
| **Model unavailable** (key blank, uncached symptom) | Diagnose: HTTP 503, "Groq LLM is not configured … Cannot produce a diagnostic without a live model" |
| Copilot with no model | HTTP 200, `llm_status=unavailable`, `reply=null`, ranking and 20 evidence records still returned |
| Review queue | 9 items |
| Corrections | 125 (component changed in 69, 55.2 %) |
| Analysis status | all 2,079 records `unscored` (this graph holds results from an older run, shown honestly as unanalysed) |

## Observations not investigated

- After Copilot turn 1 the returned `case_state.symptoms` was empty although the message described a symptom;
  the ranking was correct. Not investigated.
- The Copilot flagged four extra identifiers as invalid; the rule is that identifiers outside the retrieved
  context are not accepted as verified.

## Limits

One aircraft, one symptom, one run, the local model key. This is not a staging result and not an accuracy
measure. Re-testing staging needs the fix released and an explicit approval, because a diagnosis calls the
model and writes a cache entry on the shared server.
