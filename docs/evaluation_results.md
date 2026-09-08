# Halite Maintenance Domain — Conflict Engine Evaluation — SUBSAMPLE N=5 seed=42

**Model:** `openai/gpt-oss-120b`  
**Date:** 2026-09-08  
**Backend:** neo4j  

> Citations stripped before processing (§T7). Confidence produced by fixed `score_confidence` (clamp [0,1]); all prior divide-by-100 numbers are void.

## Invalidated Numbers

The following were computed with the old `score_confidence` / 100 bug:

- All threshold-sweep coverage and precision figures from previous reports
- The '67.4%' and '66.7%' engine accuracy claims (confidence-gated)
- The '0.65 ceiling' (was a bug symptom, not a real ceiling)

**Still valid** (pure detection / pairing, no confidence used):

- Baseline (most-recent-prior) recall: see Partitions section below

## Overall Metrics (N_gt=5, N_neg=5)

### Confusion Matrix — Baseline

| TP | FP | FN | Precision | Recall | F1 | FCR |
|---|---|---|---|---|---|---|
| 3 | 5 | 2 | 0.375 | 0.600 | 0.462 | 1.000 |

### Confusion Matrix — Engine (threshold=0.72)

| TP | FP | FN | Precision | Recall | F1 | FCR | Coverage | AA-Prec |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Confidence Distribution (positives only, N=5)

| min | p25 | median | p75 | max |
|---|---|---|---|---|
| 0.500 | 0.500 | 0.500 | 0.650 | 0.650 |

## Partition Analysis

| Partition | N | Baseline Recall | Engine Recall (t=0.72) |
|---|---|---|---|
| Easy | 3 | 1.000 | 0.000 |
| Hard | 2 | 0.000 | 0.000 |

## Threshold Sweep

| Threshold | Coverage | AA-Prec | TP | FP | Recall | F1 | Routed |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.900 | 0.800 | 4 | 0 | 0.800 | 0.889 | 1 |
| 0.55 | 0.300 | 0.500 | 1 | 0 | 0.200 | 0.333 | 7 |
| 0.60 | 0.200 | 0.500 | 1 | 0 | 0.200 | 0.333 | 8 |
| 0.65 | 0.200 | 0.500 | 1 | 0 | 0.200 | 0.333 | 8 |
| 0.70 | 0.000 | 0.000 | 0 | 0 | 0.000 | 0.000 | 10 |
| 0.75 | 0.000 | 0.000 | 0 | 0 | 0.000 | 0.000 | 10 |
| 0.80 | 0.000 | 0.000 | 0 | 0 | 0.000 | 0.000 | 10 |
| 0.85 | 0.000 | 0.000 | 0 | 0 | 0.000 | 0.000 | 10 |
| 0.90 | 0.000 | 0.000 | 0 | 0 | 0.000 | 0.000 | 10 |
| 0.95 | 0.000 | 0.000 | 0 | 0 | 0.000 | 0.000 | 10 |

## Threshold Recommendation

Recommended: **0.50** (max F1 criterion).  
Coverage=0.900, AA-Prec=0.800, Recall=0.800, F1=0.889.  

## Limitations

- N is small (single year, one dataset).
- Negative labels are weak (absence of link ≠ no conflict).
- External model subject to rate limits (200K TPD).
