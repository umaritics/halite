---
id: dec-staging-corpus-analysis-complete
title: Record staging full-corpus conflict analysis (local LLM)
status: accepted
owners: [Umar, Usman]
updated: 2026-11-16
---

# DEC-20261116 — Staging corpus analysis complete

## Context

FYP-I Final task 7 required analysing the full maintenance corpus on staging.
Mid-I left ~2,079 records `unscored`. Groq free-tier TPD blocked bulk backfill.
Staging switched to Docker-internal Ollama (`DEC-20261115-local-ollama-staging`)
with `MAINT_ANALYSIS_MODE=cascade` and `phi4-mini`.

## Decision

1. Treat **2026-11-16 ~04:16 UTC** as the staging **coverage milestone**: Neo4j
   reports **0 unscored** for 2,079 `ServiceRecord` nodes after ops backfill
   (`scripts/vm/run_analysis_backfill.sh`, 86 API rounds).
2. Persist evidence in `docs/mid1/25_local_llm_staging_evidence.md` and Neo4j
   counts; do **not** claim held-out F1 or diagnostic accuracy from this run alone.
3. **~494** rows `needs_review` is an honest outcome for a 4B local classifier;
   supervisor review is the intended next step (human gate, not auto-tune to hide).

## Snapshot (Neo4j after completion)

| analysis_state | count |
| --- | ---: |
| scored | 1,585 |
| needs_review | 494 |
| unscored | 0 |
| reviewed | 0 |

Methods (from final backfill status payload): **1,043 screen**, **801 llm**,
**235 llm-escalated**.

## Consequences

- UI Service Records and Asset History show confidence/analysis state for the
  full fleet (except legacy read normalisation).
- Review Queue is populated; claims must say “analysed, many awaiting review,”
  not “fully auto-accepted.”
- FYP-I Final tasks **3–4** (hybrid retrieval, RQ evaluation) remain open.
- Quality audit on 141 FAA pairs against `phi4-mini` is follow-up work.

## Owners

Umar (VM ops, evidence), Usman (analysis API/engine contract).