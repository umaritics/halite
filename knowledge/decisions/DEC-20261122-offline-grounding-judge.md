# Offline L4 grounding-judge instrument

Status: implemented and hosted verified on 8d3abab / run 44982604273; actual measurements pending.
Owners: Muhammad Usman Al Haq. Date: 2026-11-22.

## Context

The master plan retains L4 and human support evaluation. Lexical tests and a
blinded packet do not demonstrate model-judge accuracy. Production thresholds
are not accepted, and saved audits must continue to replay exactly.

## Decision

Build a separate explicit Ollama instrument using the existing standard-library
transport. Preserve full exact claims/single reports, fixed prompts/options,
model digest and raw judgments. Require verifiable source quotes for positive
verdicts while explicitly not treating quote existence as entailment. Retain
failures; reject incomplete full-set metrics. Compare only against complete,
independent human labels with explicit adjudication, keeping fit and validation
separate. The real 150-pair packet fits the declared 8192-token context without truncation.
Do not add a runtime dependency, enable a judge or tune on 2025.

## Consequences

This permits a reproducible L4 measurement after an endpoint/model is deliberately
selected. It does not provide measured accuracy, replace generated-prose/no-evidence
comparison or authorize borderline judgments in live sessions. Actual human/model
measurements and student threshold/whitelist decisions remain explicit gates.
