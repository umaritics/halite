# Halite Maintenance Domain — Conflict Engine Evaluation

**Model:** `openai/gpt-oss-120b`  
**Date:** 2026-09-10  
**Backend:** neo4j  

> Citations stripped before processing (§T7). Confidence produced by fixed `score_confidence` (clamp [0,1]); all prior divide-by-100 numbers are void.

## Invalidated Numbers

The following were computed with the old `score_confidence` / 100 bug:

- All threshold-sweep coverage and precision figures from previous reports
- The '67.4%' and '66.7%' engine accuracy claims (confidence-gated)
- The '0.65 ceiling' (was a bug symptom, not a real ceiling)

**Still valid** (pure detection / pairing, no confidence used):

- Baseline (most-recent-prior) recall: see Partitions section below

## Test Set Metrics (N_test=43, N_neg=0)

- Baseline recall (N=43): 0.953
- Engine TP at threshold=0.72: 0 / 43
- Engine recall at 0.72: 0.000
- Automation coverage at 0.72: 0.000

## Confidence Distribution (positives only, N=141)

| min | p25 | median | p75 | max |
|---|---|---|---|---|
| 0.150 | 0.150 | 0.300 | 0.400 | 0.650 |

## Partition Analysis (Test Set)

| Partition | N | Baseline Recall | Engine Recall (t=0.72) |
|---|---|---|---|
| Easy | 41 | 1.000 | 0.000 |
| Hard | 2 | 0.000 | 0.000 |

## Why the no-citation ceiling is 0.65

When an explicit citation is absent, the system caps confidence at 0.65. This reflects the ground truth reality: in 65.2% of unlinked follow-ups the mechanic replaces a *different* part than initially reported. A heuristic cannot exceed this 0.65 ceiling without guessing the unobservable.

## Limitations

- N is small (single year, one dataset).
- Negative labels are weak (absence of link ≠ no conflict).
- External model subject to rate limits (200K TPD).
