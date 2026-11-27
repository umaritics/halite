# Frozen research operating-point decision — Muhammad Usman Al Haq

## Recorded user decision

On 21 November 2026, after receiving OPERATING_POINT_REVIEW.md with counts and
intervals, Usman explicitly answered **“Freeze 0.80 answer / 0.50 gain (Recommended)”**.
The question specified research evaluation, not deployment or repair approval.
This document records that answer; the explanation below is AI-assisted drafting.

## Fixed choice and rationale

For `mid_heuristic-v1`, the information-gain policy uses answer threshold **0.80**,
minimum expected gain **0.50 bits**, at least **two** supporting records for the
leading named hypothesis and at most **three** questions. The primary attribute
pool is all thirteen report attributes, with structured-only and coded-only
controls retained. Belief parameters and attribute vocabulary remain fitted on
2023; no 2025 information changes this choice.

The selected 2024 point answers 23/389 cases: 16 top-one matches, seven top-one
misses, 17 top-three matches and six top-three misses. It abstains on 366 and uses
1.26 simulated questions per case. Top-one accuracy is 69.57% with a 47.62–88.89%
cluster-bootstrap interval, and coverage is 5.91% [3.73–8.45%]. This is a cautious
research trade-off accepting low coverage to reduce wrong suggestions and
question burden. No numerical safety/monetary error-cost ratio was supplied.
The broader 0.75/0.50 alternative answers ten additional cases with five more
matches and five more misses at the same average question burden.

The choice does not make a support value a fault probability. Bars remain
**relative support**. Correction parts are outcome-key proxies, not fault-cause
truth, and no output certifies airworthiness or approves a repair. Original-report
simulated answers may reuse narrative information; controls remain necessary.

## Before the held-out test

The full 2024 table, accepted row, belief/attribute/codebook files, relevant method
sources and this decision are fingerprinted by the selected-policy/protocol files.
The 2025 archive has not been opened for selection. Primary evaluation retains all
eligible 2025 occurrence-year pairs under the existing temporal/chain filtering.

A pre-test audit found that all 2023 fit outcome labels were submitted by April
2024, while four 2024 selection labels arrived in January 2025 (latest 2 January).
The primary occurrence-year test remains unchanged. A predeclared sensitivity
stratum includes only queries strictly after that latest selection-label time,
with the overlap count and separate intervals reported. This avoids presenting
an occurrence-year split as an entirely prospective calendar-time experiment.
No outcome is excluded silently or used to retune the accepted parameters.

## Scope of acceptance

This accepts the research point for frozen evaluation. It does not select sentence
support thresholds/whitelist, a language model, probability wording, teammate
review, merge or deployment. Runtime activation remains explicit and disabled by
default until the integration/release gates are satisfied.
