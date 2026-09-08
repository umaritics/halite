# Halite Maintenance Domain — Conflict Engine Evaluation

This report details the evaluation of the maintenance conflict engine against ground-truth FAA SDRs.
The explicit citations ('SUPPLEMENTAL REPORT FOR...') were stripped from the superseding records before processing.

## Overall Metrics
- **Ground truth pairs evaluated (N):** 141
- **Negative samples evaluated (N):** 0
- **Baseline (most-recent) detection accuracy:** 99.3% (N=141)
- **Engine detection accuracy:** 67.4% (N=141)
- **Engine adjudication accuracy:** 66.7% (N=141)

## Threshold Sweep

| Threshold | Precision | Recall | Automation Coverage | False Conflict Rate |
|---|---|---|---|---|
| 0.50 | 0.000 | 0.000 | 0.021 | 0.000 |
| 0.55 | 0.000 | 0.000 | 0.021 | 0.000 |
| 0.60 | 0.000 | 0.000 | 0.021 | 0.000 |
| 0.65 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.70 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.75 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.80 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.85 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.90 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.95 | 0.000 | 0.000 | 0.000 | 0.000 |


*Note: Precision within the auto-accepted subset is listed in the Precision column.*