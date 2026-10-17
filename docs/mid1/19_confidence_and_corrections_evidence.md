# Confidence, fleet records, and corrections evidence — 2026-10-17

Scope: conflict analysis, Service Records, and corrections only. Diagnostic
Copilot behavior, `/diagnose`, Graph UI/reset, CI workflows, and shared staging
were not changed. The task explicitly waived normal Mid-I file ownership.

## Runtime implementation

- Ingest: `status=unscored`, `analysis_state=unscored`, `confidence=null`.
- Migration: `scripts/migrate_conflict_analysis_state.py`, dry-run unless
  `--apply`; `--restore` only restores an untouched migrated row.
- Analysis: CLI resume and ops-token `POST /api/maintenance/analysis/run`
  (batch 1–25), live Groq only, bounded 429 retry.
- Coverage: `GET /api/maintenance/analysis/status`.
- Fleet data: paginated `GET /api/maintenance/records` and
  `GET /api/maintenance/corrections`, filtered in the backing store.
- UI: honest confidence states, fleet-wide Service Records, correction links,
  Review Queue coverage and Detected corrections tab.
- Effective confidence threshold was already consistently `0.50` in
  `backend/config.py` and `backend/.env.example`; it was not tuned.

## Automated verification

Backend (local Neo4j variables explicitly blank; pytest cache disabled because
this Windows filesystem blocked pytest's temporary cache rename):

```text
cd backend
python -m pytest -p no:cacheprovider -q
157 passed, 23 skipped in 7.55s
```

The 23 skips are the parameterized live-Neo4j cases. Docker was checked and
was unavailable:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

Frontend:

```text
cd frontend
npm test
Test Files  12 passed (12)
Tests       123 passed (123)

npm run build
✓ 854 modules transformed.
✓ built in 6.20s
```

The build retained the existing large-chunk warning. `npm ci` reported 15
dependency advisories; no broad dependency upgrade was attempted in this task.

## Mutation checks (temporary changes reverted)

1. Changed “Not analysed” to “Analysed”: the unscored state test failed.
2. Changed the All-aircraft option value from empty to `all`: the default
   filter test failed.
3. Inverted `component_changed`: the corrections filter test failed (`VALVE`
   returned where `PUMP -> PRESSURE SWITCH` was required).

After reverting all three mutations, the full suites above passed.

## Real corpus and live Groq run

Input was the real local `sdr_poc_corpus.csv`: 2,079 records across 118
aircraft. The graph was in memory; no Neo4j or staging write occurred. The
configured live model was `qwen/qwen3.8-27b`, threshold `0.50`, with the engine
default of five self-consistency passes.

Command:

```text
cd backend
python scripts/verify_confidence_corrections.py \
  --corpus "<local backend>/data/processed/sdr_poc_corpus.csv" \
  --simulate-legacy --progress-every 10
```

Migration output on the ephemeral copy:

```json
{
  "migration_dry_run": {
    "mode": "dry_run",
    "would_change": 2079,
    "before": {"total": 2079, "legacy_placeholders": 2079, "unscored": 2079, "scored_or_reviewed": 0, "with_legacy_confidence": 0},
    "after": {"total": 2079, "legacy_placeholders": 2079, "unscored": 2079, "scored_or_reviewed": 0, "with_legacy_confidence": 0}
  },
  "migration_apply": {
    "mode": "apply",
    "changed": 2079,
    "before": {"total": 2079, "legacy_placeholders": 2079, "unscored": 2079, "scored_or_reviewed": 0, "with_legacy_confidence": 0},
    "after": {"total": 2079, "legacy_placeholders": 0, "unscored": 2079, "scored_or_reviewed": 0, "with_legacy_confidence": 2079}
  }
}
```

The full analysis could **not** complete: Groq's 200,000 tokens/day quota was
already nearly exhausted. Bounded retries ended on HTTP 429 after 103 records.
This is partial evidence, not a corpus result:

```json
{
  "completed": false,
  "error": "Groq API error: Error code: 429 - tokens per day limit 200000; used 199716; requested 424",
  "processed": 103,
  "partial": {
    "elapsed_seconds": 261.85,
    "analysis_status": {
      "total": 2079,
      "unscored": 1976,
      "scored": 102,
      "needs_review": 1,
      "reviewed": 0,
      "by_label": {"contradicts": 1, "no_candidates": 40, "no_conflict": 15, "scope_disjoint": 27, "supersedes": 20}
    },
    "model_records": 63,
    "live_llm_requests": 75,
    "review_queue_size": 1,
    "supersedes_edges": 20,
    "corrections_summary": {"total_corrections": 20, "component_changed": 13, "component_changed_pct": 65.0},
    "distribution": [
      {"analysis_state": "needs_review", "label": "contradicts", "score_range": "(0,0.5)", "count": 1},
      {"analysis_state": "scored", "label": "no_candidates", "score_range": "0", "count": 40},
      {"analysis_state": "scored", "label": "no_conflict", "score_range": "(0,0.5)", "count": 13},
      {"analysis_state": "scored", "label": "no_conflict", "score_range": "[0.5,0.75)", "count": 2},
      {"analysis_state": "scored", "label": "scope_disjoint", "score_range": "(0,0.5)", "count": 15},
      {"analysis_state": "scored", "label": "scope_disjoint", "score_range": "[0.5,0.75)", "count": 12},
      {"analysis_state": "scored", "label": "supersedes", "score_range": "[0.5,0.75)", "count": 17},
      {"analysis_state": "scored", "label": "supersedes", "score_range": "[0.75,1.0]", "count": 3},
      {"analysis_state": "unscored", "label": "none", "score_range": "null", "count": 1976}
    ]
  }
}
```

## Reconciliation with old evidence

A model-free preflight over all 2,079 real records found 244 `no_candidates`
and 1,835 records with at least one positive-score prior. This materially
differs from the old claim that about 1,617 had no candidate and about 460
needed the model. Cause: the current pairing code treats any one matching
signal—including common location/JASC/part values or a 30-day window—as a
candidate. The old counts are literal prose written by
`evaluate_conflict_detection.py`, not recomputed full-corpus output.

No routing threshold or positive-score pairing weights were changed to make
the new numbers resemble the old report. Score-zero pairs are now excluded
because they have no pairing evidence. The partial 65.0% component-change rate
is close to the documented 65.2%, but 20 pairs are insufficient to call it a
full-corpus confirmation. The old 121/117/4 distribution was not reproduced
because the live quota stopped the run.

## UI state descriptions

- Unscored: “Not analysed”, no number.
- Scored/no relation: “No conflict found (k comparisons)”.
- Scored relation: label plus score, tooltip states heuristic/not probability.
- Superseded: confidence hidden; “Corrected by <record> — component changed X
  → Y” links to the correcting history record.
- Service Records: All aircraft selected by default, total plus Load more,
  tail on each row, URL-backed filters.
- Review Queue: coverage-aware empty message; Detected corrections tab has
  live cards, All-aircraft default, paired findings and evaluation footnote.

## Staging command sequence (not executed)

Only run after explicit approval and a backup:

```text
cd backend
python scripts/migrate_conflict_analysis_state.py
python scripts/migrate_conflict_analysis_state.py --apply
python scripts/backfill_conflict_scores.py --resume
```

Or operate bounded API batches with the configured ops token:

```text
GET  /api/maintenance/analysis/status
POST /api/maintenance/analysis/run
X-Ops-Token: <configured token>
{"batch_size":25}
```

Shared staging was not read or mutated for this verification.
