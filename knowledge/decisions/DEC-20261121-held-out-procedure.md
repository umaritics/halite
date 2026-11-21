# Validate and execute the frozen held-out procedure without tuning

- Status: implemented; synthetic/full-stack verification pending; real access gated
- Date: 2026-11-21
- Owner: Usman

## Context

Usman selected .80/.50 on the verified 2024 evidence. The accepted policy and
pre-test chronology protocol are frozen. A real 2025 run needs reproducible
source receipts and a tested procedure, without another threshold search.

## Decision

Freeze procedure/verifier/workflow/test hashes before access. Validate historical
source fingerprints before downloading 2025 and write a pre-access receipt.
Reuse original temporal/chain filtering, fixed ranker/fit/schema and simulation.
Keep all cohorts/strategies/budgets/part-change and label-availability strata,
1000 original-report bootstrap intervals, named-top ECE and retrieval-miss counts.
Use identical selected-policy terminal beliefs/questions for abstention-off,
removing only confidence/evidence answer gates. Independently recalculate point
metrics and replay every interval from saved cases.

Ordinary PRs run preflight and synthetic tests only. A separate hosted job needs
the explicit run-frozen-held-out label event and successful exact-head full CI.
Remove the label after dispatch so later documentation pushes do not reopen data.
Retain results/traces/receipts and compressed source artifacts. No staging/model
endpoint, local heavy evaluation, raw CSV commit or runtime activation.

## Consequences

No 2025 tuning or vocabulary changes are permitted. Bad results are reported
with intervals. The legacy Mid-I ranker had prior prototype exposure to a 2025
POC; this is a frozen-configuration temporal test rather than a claim that the
project never saw any 2025 report. The primary occurrence-year case set and
predeclared chronology sensitivity are retained without silently omitting cases.

## Exact history restoration before test access

Attempt 44905292132 stopped before 2025: FAA appended one 2024 record. All
original rows and the complete 2023 archive remain unchanged. An identifier/
order-only manifest reconstructs the frozen history and requires its original
complete projection SHA. Retrieved revisions are retained and restoration is
recorded in the receipt. Missing/modified original content is rejected. This
preserves the actual approved training/selection inputs instead of relaxing
hashes or using newly appended rows. Synthetic tests cover restoration and
failure paths; method/index hashes are frozen before held-out access.
