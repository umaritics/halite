# Freeze the user-selected research point before held-out access

- Status: accepted choice; implementation complete; hosted preflight verification pending
- Date: 2026-11-21
- Owner: Usman

## Context

After the verified 2024 comparison and concrete review table, the user explicitly
answered “Freeze 0.80 answer / 0.50 gain (Recommended)”. This resolves the
master-plan numeric-choice gate for research evaluation, without approving
runtime activation, probability wording, other research choices or deployment.

## Decision

Record the user answer and AI-assisted rationale. Freeze the all-attribute
information-gain point with n_min=2/max_questions=3, exact 2024 row, fit/schema/
codebook/method/decision hashes. The pre-test protocol pins that policy and
refuses refitting, threshold sweeps, missing metrics or control removal.
CI preflight validates without reading 2025; tests reject meaningful mutations.

## Chronology audit

Frozen 2023/2024 projection fingerprints were recomputed before extracting
label dates. All fit labels are available by April 2024. Four selection labels
arrive in January 2025, latest 2 January. Preserve the primary occurrence-year
case definition and predeclare an additional post-label-availability stratum,
with overlap counts and separate intervals. This exposes the small timing
overlap rather than silently drop cases or assert a fully prospective split.

## Consequences

The research point is accepted and frozen. Held-out execution/results, owner
review/merge, runtime activation and final report/other human research gates
remain. The saved selection artifact itself stays unchanged as a historical
unselected snapshot; the separate selected-policy file records later acceptance.
