# 2024 operating-point review — awaiting Usman’s choice

This is AI-assisted analysis for Usman to review, not his recorded decision. No
operating point is installed or selected, and 2025 remains untouched.

The combined answer/ask/abstain rule was applied to 389 correction pairs from 340
original reports. Each point uses at least two evidence records and at most three
questions. The grid was fixed before the comparison. All original-report answers
are simulated report fields, not new technician observations.

## Concrete choices for the all-attribute information-gain policy

Values are percentages with original-report cluster-bootstrap 95% intervals,
except questions (mean over every case). Full tables retain all three cohorts,
random/no-question controls and part-change strata.

| Answer / gain threshold | Answered / 389 | Coverage % [95% CI] | Top-1 % among answered [95% CI] | Top-3 % among answered [95% CI] | Top-3 misses / all % [95% CI] | Questions / case [95% CI] |
| --- | --- | --- | --- | --- | --- | --- |
| 0.50 / 0.10 | 117 | 30.08 [24.87, 35.52] | 43.59 [34.96, 53.23] | 57.26 [48.78, 67.29] | 12.85 [9.07, 16.67] | 2.34 [2.25, 2.44] |
| 0.75 / 0.50 | 33 | 8.48 [5.03, 12.54] | 63.64 [43.89, 87.10] | 66.67 [46.87, 90.00] | 2.83 [0.72, 5.82] | 1.26 [1.20, 1.33] |
| 0.80 / 0.50 | 23 | 5.91 [3.73, 8.45] | 69.57 [47.62, 88.89] | 73.91 [53.85, 91.67] | 1.54 [0.49, 3.00] | 1.26 [1.20, 1.33] |
| 0.95 / 0.25 | 10 | 2.57 [1.06, 4.26] | 80.00 [50.00, 100.00] | 80.00 [50.00, 100.00] | 0.51 [0.00, 1.34] | 2.14 [2.02, 2.26] |

## Proposed research choice, not acceptance

I propose **answer threshold 0.80 and minimum gain 0.50 bits** as a conservative
research operating point for the existing all-attribute policy. On 2024 it answers
23/389 cases: 16 top-one keys match, 17 top-three lists contain the correction key,
and six answered lists miss that key. The other 366 cases abstain. It uses an
average 1.26 simulated questions per case. The confidence intervals are wide.

This proposal gives up answer coverage to limit unsupported suggestions and
question burden. It does not establish that 0.80 means 80% probability: observed
top-one accuracy is 69.57% with a 47.62–88.89% interval. The bars must remain
**relative support**. The 0.95/0.25 row has only ten answered cases; its apparent
80% accuracy has a 50–100% interval, so the point estimate is not strong evidence.

The 0.75/0.50 alternative answers ten additional cases with the same average
question burden: five more top-one matches and five more top-one misses; its
top-three lists add five matches and five misses. Choosing between these points
therefore requires weighing extra answered cases against wrong suggestions.
No monetary or safety cost ratio has been invented. Abstention still exposes
the historical ranking and directs users to approved documentation/personnel.

## Scope and required decision

These are selection-set outcome-key proxies, not fault-cause truth, sentence
hallucination rates, causal benefits or airworthiness approval. All-attribute
questions can reuse initial narrative information; the structured/coded controls
remain in the full evidence. No claim of strategy superiority is made from
separate point intervals.

Usman must choose the thresholds (or another fixed-grid point), state the
preference about wrong suggestions versus extra questions, and approve this as
the frozen research operating point before the held-out 2025 evaluation. The
uncited-sentence whitelist and grounding thresholds remain separate decisions.

Evidence: [hosted sweep and independent verification](https://github.com/umaritics/halite/actions/runs/44883664943).
The full 4,536-row JSON/CSV is in `backend/investigation/experiments/results/policy_selection_2024_v1/`.
Its JSON SHA-256 is `6b628bec427c153d7015b7526f8c0b908ce0e8884878a0fbf6916759c299a27e`.

## Subsequent user decision

Usman explicitly selected **0.80 answer / 0.50 gain** after this review. The
acceptance and frozen-input details are recorded in
`docs/fyp1-final/OPERATING_POINT_DECISION.md`. This original review remains as
the evidence shown before that choice; 2025 was not used to select it.
