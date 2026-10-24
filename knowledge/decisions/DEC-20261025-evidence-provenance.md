---
id: dec-diagnostic-evidence-provenance
title: Consolidate diagnostic evidence without altering retrieval semantics
status: accepted
owners: [Umar, Shahmeer]
updated: 2026-10-25
---

# DEC-20261025 — Diagnostic evidence consolidation and provenance

## Context

The D3B.1 investigation rail repeated Case State observations and Live Ranking
scores, then rendered every FAA SDR narrative expanded. Fleet matches from other
aircraft looked like evidence about the selected aircraft even though copilot
retrieval intentionally excludes the selected asset from its fleet scan.

## Decision

- Case State remains the authoritative structured view of extracted symptoms,
  observations, completed checks, and ruled-out components. The conversation
  retains the technician's original wording.
- Live Ranking remains authoritative for component position, heuristic score,
  and the score-not-probability disclaimer.
- Evidence records are grouped only when their exact aircraft identity,
  component, and condition agree. Missing grouping fields keep a record separate.
- Aircraft comparison uses exact, case-normalized known UUID/tail identifiers.
  Prefix, suffix, punctuation removal, and substring matching are forbidden.
- The inspector preserves every cited ID and exact source date, reports cited and
  retrieved counts separately, previews three reports per group, and puts the
  original narrative behind an individual disclosure.
- Other-aircraft matches remain visible and keep their backend ranking semantics;
  the UI labels provenance and supported discrepancy-type differences only.

## Consequences

- Repetitive SDR evidence is compact without fabricating a combined event or an
  LLM-authored summary.
- A differently formatted identifier is unverified or different unless the
  asset list provides an exact mapping.
- Evidence inspection remains read-only and cannot invoke copilot inference,
  conflict classification, or ranking animation.
- `symptoms` and `observations` remain separate; taxonomy changes require a
  backend contract follow-up.

## Owners

Umar, Shahmeer

## Date

2026-10-25
