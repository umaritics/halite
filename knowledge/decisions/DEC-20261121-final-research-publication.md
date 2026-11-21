# Publish the accepted selection point and frozen test without a new experiment

- Status: implemented and verified; owner review pending
- Date: 2026-11-21
- Owner: Usman; shared-caption review: Shahmeer

## Context

The user accepted .80/.50 and the actual frozen 2025 run is independently
verified. The product still exposes only the earlier selection studies. The
master plan requires every result to be visible from committed evidence.

## Decision

Use publication/transport v2 with fixed checksum-pinned sources. Validate the
real frozen policy/protocol and independent test report before serving results.
Project the 756 existing joint-selection rows at accepted gain .50, retaining
the full source hash. Mark .80 only on the accepted all-attribute IG/all-case
2024 curve. Do not mark that point on the historical pre-question curve.

Make the fixed 2025 test the default view. Show its saved question curves,
fixed stopping points/control comparisons, sample sizes, exact intervals,
valid-draw counts, ECE, timing sensitivity and retrieval-miss/proxy disclosures.
No test-year sweep is inferred from the selection curve. Preserve undefined
zero-answer accuracy and the same-terminal-state abstention-off definition.

Use existing shared primitives/Recharts. Prepare a minimal shared-caption stage
option for Shahmeer review so test figures are labelled held-out. Verification
uses real-artifact component/integrity tests and the hosted full-stack browser
in both themes at 1280/390px. No laptop builds/model jobs/staging writes.

## Consequences

Only saved values are displayed; no fit/rerank/sweep/download or live activation
is added. The version change is explicit and malformed/stale publications fail.
The existing raw experiments, selected-policy bytes and pre-test protocol remain
unchanged. Human calibration/model measurements/report/release gates remain.

Runtime packaging checks the actual backend policy/protocol and every pinned
backend input relative to the installed backend root. The backend-only Docker
image does not contain project docs. Full documentation/source preflight stays
in CI and remains byte-for-byte unchanged; publication does not require a fake
repository mount. An isolated backend-only package test and the real Compose
API/browser verify this boundary. Documentation/audit hashes remain provenance
in the frozen policy and are verified by the original CI preflight.
