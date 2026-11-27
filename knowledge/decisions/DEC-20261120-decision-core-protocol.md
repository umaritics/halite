---
id: dec-decision-core-protocol
title: Honest decision inputs and temporal calibration protocol
status: accepted
owners: [Usman]
updated: 2026-11-20
---

# Decision core and selection protocol

## Status

Accepted engineering implementation. Numeric operating point and full empirical
acceptance remain pending. The user authorized the AI-assisted design draft on
his behalf; no manual labels, approvals or unaided authorship are claimed.

## Context

Rank scores are not probabilities. Persistence/UI already work but cannot justify
answering from an unmeasured policy. The guide conflicts with the shared contract
on fit year, and real cases may share an original report or arrive after it.

## Decision

Implement pure belief/entropy and policy functions; keep production policy
unconfigured and expose relative support only. Store exact beliefs/entropy on
new snapshots. Use the shared contract: 2023 fit, 2024 selection, 2025 held out.
Keep every eligible known-outcome correction pair, exclude the query's entire
citation chain and every equal/later submission, and cluster bootstrap by original
report. An exploratory earliest-correction-only run was replaced before held-out
evaluation because it omitted eligible pairs. Record source/method fingerprints,
parameter search domains, exclusion counts, sample counts and undefined metrics.

## Consequences

A green maths test is not a calibrated diagnostic product. Operating-point choice,
questions, sentence grounding, held-out results, labels and final product charts
remain required. Empirical negatives must be reported and analysed. An explicit
other bucket represents retrieval misses; it does not certify the unknown cause.

## Owners

Usman: investigation implementation and AI-assisted design review. Umar retains
retrieval/corpus ownership; these research adapters consume sources without editing
his implementation. Shared owner-review and staging gates remain unchanged.
