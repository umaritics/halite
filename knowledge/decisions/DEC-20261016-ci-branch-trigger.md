---
id: DEC-20261016-ci-branch-trigger
title: CI push trigger includes Umar Mid-I branch
status: accepted
owners: [Umar, Usman]
updated: 2026-10-16
---

# DEC-20261016 — CI branch trigger

## Context

`.github/workflows/ci.yml` only auto-ran on `main`, `develop`, `usman`. Umar’s Mid-I branch would otherwise rely solely on pull_request events.

## Decision

Add the Umar Mid-I push branch to `on.push.branches`. Current value: **`umar/mid1-graph-diagnostics`** (earlier temporary name `feat/mid1/graph-diagnostics` removed).

## Consequences

Pushes to the Umar Mid-I branch run the same three jobs. PRs still covered. Usman remains CI owner for broader workflow design.
