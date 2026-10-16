---
id: dec-main-only-staging-release
title: Main-only, CI-gated staging releases
status: accepted
owners: [Umar, Usman]
updated: 2026-10-16
---

# DEC-20261016 — Main-only, CI-gated staging releases

## Context

Umar and Usman's Mid-I branches are integrated. Allowing either obsolete
branch to deploy can overwrite the reviewed staging revision. Manual refs were
also interpolated before validation, and the full CI workflow currently remains
red on a known Shahmeer-owned frontend test.

## Decision

1. Automatic staging release follows only a successful full CI run for the
   current `main` tip.
2. Manual deploy and rollback accept only a full commit SHA reachable from
   `main`, require an exact operation confirmation, and require successful CI
   for that SHA.
3. All releases use the existing `staging` GitHub Environment; administrators
   configure required reviewers there.
4. The workflow records the previously deployed SHA before mutation and
   verifies the exact approved SHA afterward.

## Consequences

- The current frontend CI failure blocks new staging releases. It is not
  weakened or bypassed by backend owners.
- Branch names and arbitrary refs cannot reach SSH commands.
- Rollback is explicit and auditable but also limited to CI-green `main`
  history.
- No secrets, VM paths, or runtime configuration change.
