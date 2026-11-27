---
id: mod-conflict
title: Conflict engine module
status: active
owners: [Usman, Umar]
updated: 2026-11-25
---

# Module: Conflict engine

## Purpose

Detect whether a new/updated `ServiceRecord` conflicts with or supersedes prior records on the same asset; route to auto-apply or human review.

## Primary files

| File | Owner |
| --- | --- |
| `backend/services/conflict_engine.py` | Usman |
| `backend/api/routes/maintenance.py` (process/review) | Usman |
| `backend/tests/test_conflict_engine.py` | Usman |
| `backend/integrity/` (`apply.py`, `citations.py`, `timeutil.py`, `validity.py`, `proposal.py`, `backfill.py`, `candidates.py`, `prompts.py`, `classify.py`) | Shahmeer |
| `backend/integrity/bench/` (citation-masked benchmark; see its [README](../../../backend/integrity/bench/README.md)) | Shahmeer |

## Pipeline

0. **Guards and rule R1** — a reviewed record is returned untouched (`skipped="reviewed"`) unless `force` is set. If the text cites a report ID (`integrity/citations.py`), `apply_explicit_citations` links to each cited report that exists, is on the same aircraft and is not known to be later (same submission time or earlier; without submission times, same occurrence date or earlier). Linked: status `auto_accepted`, confidence 1.0, method `explicit_citation`, model `rule-R1`, no model call. Cited report not in the corpus: `no_action`, label `cited_prior_missing`. Cited report present but ineligible: the normal path runs and the result carries `citation_ineligible` with reasons.
1. **Candidate pairing** — same-asset history, positive heuristic score, cap (`MAINT_MAX_CANDIDATES`, often 25). Score-zero records are not candidates. A prior is eligible only if it was submitted before the target (`integrity/timeutil.py`, timezone-aware; occurrence date decides only when a submission time is missing). Pairs a reviewer rejected are skipped.
2. **Classify** — LLM JSON label (`supersedes`, `partial_supersedes`, `contradicts`, `no_conflict`, `scope_disjoint`) with cache.
3. **Adjudicate + confidence** — evidence signals (citation language, recency, authority, part/JASC agreement).
4. **Route** — high-risk labels → `needs_review`; else confidence vs `MAINT_CONFIDENCE_THRESHOLD`.

## Candidates, prompt and votes live in `integrity/`

The engine no longer holds its own candidate ranking, prompt text or vote logic. It calls:

- `backend/integrity/candidates.py` — `PAIR_WEIGHTS`, `pair_score` and `rank_candidates`. These are pure functions over plain
  record dicts. The engine still reads the asset history from the graph (`list_asset_history`, limit 200, so the oldest 200
  reports of an aircraft) and hands it to `rank_candidates`. Three orderings exist: `legacy` (score, date, id; legacy mode),
  `containment` (text overlap first; cascade mode, which staging runs) and `submission_gap` (benchmark only).
- `backend/integrity/prompts.py` — the system prompts. `v1` is the staging prompt, byte for byte, and is pinned by a SHA-256
  test (`test_prompt_v1_is_pinned_to_the_staging_bytes`). `v2-unannounced` is a draft for the benchmark only. Staging does not use it.
  Changing the staging prompt needs Shahmeer's decision.
- `backend/integrity/classify.py` — `parse_classification`, the user prompt and `classify_pair`, the majority vote, without the
  engine's file cache.

This was a refactor with no behaviour change. The point is that the benchmark calls the same code staging runs.
`conflict_engine.py` imports these names, so existing callers still work.

## Integrity writes and links

All `SUPERSEDES` / `NOT_SUPERSEDES` links, status changes and review fields are written by
`backend/integrity/apply.py`; the engine and the review routes call it. It takes an `audit(action, record_id, metadata)`
callable from the route and emits `integrity.link.created`, `integrity.link.removed` and `integrity.status.changed`.
A human-decided record (`analysis_state=reviewed` or status `accepted`/`rejected`) is not overwritten.

A `SUPERSEDES` link is one edge per ordered pair with `scope`, `confidence`, `rationale`, `created_at`, `method`
(`explicit_citation`, `model` or `human`), `model_version`, `decided_by`, `decided_at`. Validity is read from these links
by `integrity/validity.py`; the `superseded` status string is still written for older readers. When a re-run no longer
proposes a prior, the earlier `model` link to it is removed; citation and human links stay.

The engine stores `proposed_prior_id`, `integrity_p` (equal to the confidence) and `integrity_model_version`
(`handweighted-v0` on the model path, `rule-R1` on the rule path) on the record. The confidence is still hand-weighted;
WP-A3 replaces it.

## Review decisions

- **Accept** confirms existing links in place (adds `decided_by`, `decided_at`) and creates a `human` link to the proposed
  prior when the label is `supersedes` or `partial_supersedes`.
- **Reject** removes the record's links and writes a `NOT_SUPERSEDES` edge to each, so the pair is not proposed again.
- Both set `analysis_state=reviewed`, add reviewer fields, add a `review_decisions` row and one
  `maintenance.review.accepted|rejected` audit event.
- `GET /maintenance/review-queue/{id}/proposal` returns the stored proposal and calls no model. A record with
  `proposed_prior_id` absent gets its prior recomputed from candidates; the mode it was scored in is inferred from
  `analysis_method` and `analysis_passes`. `python -m integrity.backfill [--dry-run]` stores the missing priors.

## Design constraints

- Do not raise threshold only to beautify demos.
- Preserve original records on accept/reject; do not claim adjudicated *diagnosis*.
- Conflict metrics ≠ diagnostic accuracy.

## Analysis state and operations

Ingest writes `unscored` with null confidence. The additive state machine is
`unscored` → `scored|needs_review` → `reviewed`. `no_candidates` is a real
`scored` result with zero comparisons, score 0, and no model call. A superseded
older record is presented through its incoming `SUPERSEDES` edge rather than a
confidence number.

The legacy migration is dry-run by default and preserves `legacy_confidence`.
Before migration, API reads identify an untouched `confidence=1.0` record with
no analysis metadata as `legacy_placeholder`, return null confidence and
`analysis_state=unscored`, and leave the stored graph value unchanged.
Backfill `--resume` and `POST /maintenance/analysis/run` select explicit
`analysis_state=unscored`; both require a **live LLM** (`groq_service.is_live`,
Groq or `LLM_PROVIDER=openai_compatible` on staging), use `allow_stub=False`, and
bound 429 retries when on Groq. The API batch is ops-token protected and capped
at 25. Coverage is returned by `GET /maintenance/analysis/status`.

### Staging inference (2026-11-16)

Shared staging runs **Docker-internal Ollama** (`phi4-mini`) via `GroqService`
openai-compatible adapter — see
[`docs/local-llm-staging.md`](../../../docs/local-llm-staging.md) and
`DEC-20261115-local-ollama-staging`. `MAINT_ANALYSIS_MODE=cascade` is enabled on
the VM. Full-corpus backfill completed with **0 unscored** (see
`DEC-20261116-staging-corpus-analysis-complete`, `docs/mid1/25_local_llm_staging_evidence.md`).
Local dev defaults remain `LLM_PROVIDER=groq`.

### Opt-in cost cascade

`MAINT_ANALYSIS_MODE=legacy` remains the default. In `cascade` mode, candidate
ties are reordered by meaningful older-text containment, with supplemental-ID
answer keys and generic boilerplate removed. Pairs below the pre-registered
0.79 text/scope score become deterministic `screen` decisions without a model
request. Remaining pairs use two votes, escalating to five only on initial
disagreement; a persistent split goes to review. Confidence scales the model
classification signal by vote agreement, never by the number of passes.

Every classification stores method, model, votes, passes, provider token
usage when available, agreement and timestamp in the cache and on the record
(votes are JSON text for Neo4j property compatibility). A UTC-day budget is
persisted per model and stops before 90% of configured request or token caps.
Cache hits do not debit it. `/analysis/status` groups stored results by method,
and `/analysis/run` returns its stop reason and remaining budget.

The effective threshold is 0.50. The 2026-10-17 real-corpus preflight found
1,835 model-eligible records under current positive-score pairing, materially
different from the old “roughly 460” evidence. Do not tune pairing or routing
to fit that old count without a ground-truth evaluation. See
`docs/mid1/19_confidence_and_corrections_evidence.md`.
The cascade’s offline evidence is in
`docs/mid1/21_analysis_cascade_evidence.md`; live quality remains for the
next round.

## Related

[FLOW-conflict-review.md](../../flows/FLOW-conflict-review.md)
