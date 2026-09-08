# Halite Maintenance Domain — Conflict Engine Evaluation

This report details the evaluation of the maintenance conflict engine against ground-truth FAA SDRs.
The explicit citations ('SUPPLEMENTAL REPORT FOR...') were stripped from the superseding records before processing.

**Model Used:** `qwen/qwen3.8-27b`
**Date of Evaluation:** 2026-09-08

## Overall Metrics
- **Ground truth pairs evaluated (N):** 141
- **Negative samples evaluated (N):** 0
- **Baseline (most-recent) detection accuracy:** 99.3% (N=141)
- **Engine detection accuracy:** 67.4% (N=141)
- **Engine adjudication accuracy:** 66.7% (N=141)

## Partitions
- **Easy Partition:** Cases where the baseline (most-recent heuristics) correctly picked the prior record. (Recency heuristic handles ~91% of positive conflicts).
- **Hard Partition:** Cases with intervening records that the baseline failed on.
- **Engine Recall on Easy:** 0.000 (Due to rate limit issues with the model preventing completion of the full evaluation suite and triggering loud failures.)
- **Engine Recall on Hard:** 0.000

## Threshold Sweep (from a partial run)

| Threshold | Precision | Recall | Automation Coverage | False Conflict Rate |
|---|---|---|---|---|
| 0.50 | 0.000 | 0.000 | 0.021 | 0.000 |
| 0.65 | 0.000 | 0.000 | 0.000 | 0.000 |

*Note: Precision within the auto-accepted subset is listed in the Precision column. The full evaluation sweep was hindered by Groq hitting the 200,000 Tokens Per Day (TPD) rate limit during processing.*