# Question selection protocol and coded-field handoff

Status: implemented offline; runtime and owner review pending
Date: 2026-11-20
Owners: Usman; shared ingest review Shahmeer

## Context

Report-code meanings require official provenance. Reusing narrative fields as
simulated answers can overstate the value of new questions. Temporal leakage can
also arise from likelihood counts, even when initial ranking is filtered.

## Decision

Pin and retain the official FAA lookup archive; extract exact descriptions.
Fit only the categorical vocabulary on 2023. Enforce strict earlier submission
and full query-chain exclusion for every likelihood snapshot. Compare all thirteen,
six structured and four coded attribute pools with information-gain/random/none
controls. Use original reports for answers and correction parts only for scoring.
Report paired intervals clustered by original; do not equate entropy with accuracy.

The user authorized preparation/testing of the twelve-line shared ingest patch on
a separate review branch before PR #27 merges: “Prepare and test the separate
review branch”. This authorizes local preparation/testing; Shahmeer review, merge
and Umar's staging backup/backfill are not represented as completed.

## Consequences

2024 is selection, not held-out evidence; 2025 remains untouched. Offline question
core can be reviewed independently of shared ingest and live answer handling.
The earlier baseline replay now lists its exact frozen source dependencies rather
than including unrelated new experiment files; its original fingerprint and every
metric still match. No old method or baseline result was changed.
