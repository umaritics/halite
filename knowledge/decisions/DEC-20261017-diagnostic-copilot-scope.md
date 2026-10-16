---
id: dec-diagnostic-copilot-scope
title: Diagnostic copilot cross-owner scope waiver
status: accepted
owners: [Umar, Shahmeer, Usman]
updated: 2026-10-17
---

# DEC-20261017 — Diagnostic copilot cross-owner scope waiver

## Context

The diagnostic copilot spans Umar-owned retrieval/API code, Shahmeer-owned
Diagnostics UI code, and the model default in Usman-owned configuration. The
team lead explicitly waived the usual Mid-I ownership boundary for this task.

## Decision

The `feat/mid1/diagnostic-copilot` change may edit only the diagnostic route,
additive diagnostic retrieval helpers, token/empty handling in the Groq
wrapper, model-default configuration, Diagnostics UI/API adapter, related
tests, and matching knowledge/evidence files. The conflict engine, ingest,
other pages, CI workflows, and graph-reset route remain out of scope.

The copilot is stateless: the client sends structured case state on every turn.
The existing `/diagnose` contract remains intact; an empty model explanation
now becomes a visible 503 instead of a blank successful response.

## Consequences

- One PR can deliver and test the end-to-end diagnostic conversation.
- Cross-owner review is still required before merge.
- The ranking remains a deterministic heuristic, never a probability.
- Live local and staging evidence must not be claimed unless health reports
  Neo4j and a live LLM and the actual responses are captured.

## Owners

Umar, Shahmeer, Usman

## Date

2026-10-17
