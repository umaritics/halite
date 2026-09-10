# Halite Maintenance Domain — Conflict Engine Evaluation

Complete over all 141 author-recorded pairs; 209 sampled negatives.
Model: `openai/gpt-oss-120b`. No results reused from any other model.

## 1. Automation Coverage
Of 2,079 records processed, a conflict was detected in **121**. Of those, **117** were resolved without human review and **4** routed to the review queue. The remaining **1,958** records had no candidate conflict and required no decision. Automation coverage is measured over records where a conflict was detected — never over the whole corpus.

## 2. Pruning Efficiency
Of 2,079 records, 1,617 (77.8%) had no candidate prior on their asset after graph-constrained pruning and required no LLM evaluation. On the largest asset (153 records), exhaustive all-pairs comparison would require 11,628 evaluations; the graph constraint plus candidate scoring reduces this to at most 25 per record.

## 3. Recall Definitions
Pair-level detection (N=141 author-recorded pairs): precision 0.788, recall 0.660
Candidate-level classification (N=350 evaluated pairs): precision 0.903, recall 0.660

The pair-level figure answers the operative question: *of the supersessions that exist, how many did you find?*

## 4. Explanation of N
There are 141 ground-truth positive pairs. The previous report's 445 positives (N=691) was an artifact of appending multiple partial runs to the CSV without deduplication. After deduplication, the true evaluated candidate-level dataset has N=350 (141 positive, 209 negative), reflecting exactly one LLM evaluation against the `best_prior` per superseding record.

## 5. Confusion Matrices (Threshold 0.50)

| System | Precision | Recall | F1 | False-conflict rate |
|---|---|---|---|---|
| Baseline (most-recent-prior) | 0.380 | 0.908 | **0.536** | **1.000** |
| Engine (t=0.50) | 0.903 | 0.660 | **0.762** | **0.048** |

> The baseline attains higher F1 by asserting a conflict on every record it evaluates. Its false-conflict rate is 1.000 — on all 209 negative pairs it claimed a supersession that does not exist. It has no mechanism to abstain. The engine detects fewer true supersessions but is wrong on 4.8% of negatives rather than 100%. In a maintenance record system, a false supersession silently invalidates a real service record, so precision and the ability to abstain are the operative properties, and F1 weighted equally across both classes does not reflect that cost asymmetry.

## 6. Threshold Sweep (N=350)

| Threshold | Baseline F1 | Engine F1 | Engine Recall | Engine Precision | Engine FCR | Engine TP | Engine FP |
|---|---|---|---|---|---|---|---|
| 0.10 | 0.536 | **0.761** | 0.667 | 0.887 | 0.057 | 94 | 12 |
| 0.20 | 0.536 | **0.761** | 0.667 | 0.887 | 0.057 | 94 | 12 |
| 0.30 | 0.536 | **0.761** | 0.667 | 0.887 | 0.057 | 94 | 12 |
| 0.40 | 0.536 | **0.756** | 0.660 | 0.886 | 0.057 | 93 | 12 |
| 0.50 | 0.536 | **0.762** | 0.660 | 0.903 | 0.048 | 93 | 10 |
| 0.60 | 0.536 | **0.422** | 0.277 | 0.886 | 0.024 | 39 | 5 |
| 0.70 | 0.536 | **0.000** | 0.000 | 0.000 | 0.014 | 0 | 3 |
| 0.80 | 0.536 | **0.000** | 0.000 | 0.000 | 0.014 | 0 | 3 |
| 0.90 | 0.536 | **0.000** | 0.000 | 0.000 | 0.010 | 0 | 2 |

## 7. Classifier Stability
**Record pair SWIA2025122876590 and SWIA2025112576494**
- `qwen/qwen3.8-27b` classified this pair as `contradicts` with rationale: "The prior record states the cracked drag angle was removed and replaced with a servicable one, while the new record claims a crack was found at the same location during inspection, implying the defect persists or was not resolved."
- `openai/gpt-oss-120b` classified the same pair as `scope_disjoint` with rationale: "The records relate to different occurrences of cracks on the drag angle."
