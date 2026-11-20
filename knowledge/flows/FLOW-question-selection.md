---
id: flow-question-selection
title: Leakage-safe simulated question selection
status: active
owners: [Usman]
updated: 2026-11-20
---

# Question selection

1. Verify official FAA lookup archive and extract exact code descriptions.
2. Freeze attribute vocabulary using 2023 only; load frozen 2023 belief parameters.
3. Load frozen 2024 baseline cases and validate the exact source fingerprint.
4. At each original SubmissionDate, count only earlier records outside its chain.
5. Select by expected information gain or seeded uniform random; no-question
   control preserves priors. Simulated answers use only the original report.
6. Apply posterior, exclude the asked attribute even for not-sure, repeat to three.
7. Score correction outcomes downstream; cluster bootstrap by original report.
8. Save traces, provenance, controls and figures; independently replay all metrics.

```mermaid
flowchart LR
  FAA[Official lookup ZIP] --> Codes[Exact codebook]
  Fit[2023 records only] --> Schema[Frozen vocabulary]
  Codes --> Schema
  Records[2023 and 2024 submissions] --> Time[Strict earlier time and chain exclusion]
  Schema --> Time
  Time --> Models[Smoothed likelihood matrices]
  Baseline[Frozen ranking and 2023 belief fit] --> Prior[Prior including other]
  Models --> Choose[EIG or seeded random question]
  Prior --> Choose
  Original[Original report fields only] --> Answer[Simulated answer]
  Choose --> Answer
  Answer --> Posterior[Bayesian update; remove asked attribute]
  Posterior --> Choose
  Posterior --> Score[Downstream accuracy and entropy scoring]
  Outcome[Correction part only] --> Score
  Score --> Evidence[Cluster intervals, traces and figure]
```

Malformed matrices/source mismatch fail explicitly; backwards temporal queries
fail; unoffered answers become not-sure in simulation; no empirical threshold is
installed automatically. Runtime session answers are still refused pending live
integration. Ingest/backfill preparation is a separate review change.
