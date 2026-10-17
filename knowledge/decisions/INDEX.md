---
id: decisions-index
title: Architecture / process decisions
status: active
owners: [all]
updated: 2026-10-17
---

# Decisions index

Newest first. Status: `accepted` | `proposed` | `superseded`.

| ID | Title | Status | Owners |
| --- | --- | --- | --- |
| [DEC-20261017-conflict-analysis-state](DEC-20261017-conflict-analysis-state.md) | Persist honest conflict-analysis state separately from confidence | accepted | Umar, Usman, Shahmeer |
| [DEC-20261017-fleet-service-records](DEC-20261017-fleet-service-records.md) | Fleet-wide paginated Service Records and corrections | accepted | Umar, Usman, Shahmeer |
| [DEC-20261017-diagnostic-copilot-scope](DEC-20261017-diagnostic-copilot-scope.md) | Diagnostic copilot cross-owner scope waiver | accepted | Umar, Shahmeer, Usman |
| [DEC-20261016-main-only-staging-release](DEC-20261016-main-only-staging-release.md) | Main-only, CI-gated staging releases | accepted | Umar, Usman |
| [DEC-20261016-frontend-reflects-backend-outputs](DEC-20261016-frontend-reflects-backend-outputs.md) | Frontend only adds to, never hides or alters, backend outputs | accepted | Shahmeer |
| [DEC-20261016-service-records-per-aircraft](DEC-20261016-service-records-per-aircraft.md) | Service Records loads one aircraft at a time | superseded | Shahmeer |
| [DEC-20261016-review-actions-server-confirmed](DEC-20261016-review-actions-server-confirmed.md) | Review Accept/Reject wait for the server; no bare-key shortcuts | accepted | Shahmeer |
| [DEC-20261016-frontend-maintenance-only](DEC-20261016-frontend-maintenance-only.md) | Frontend is maintenance-only; legacy software UI unreachable | accepted | Shahmeer |
| [DEC-20261016-shared-staging-cd](DEC-20261016-shared-staging-cd.md) | Centralized staging API + Actions CD | accepted | Umar, Usman |
| [DEC-20261016-knowledge-rename](DEC-20261016-knowledge-rename.md) | Move bank to top-level `knowledge/` | accepted | Umar |
| [DEC-20261016-context-bank](DEC-20261016-context-bank.md) | Adopt knowledge bank + agent protocol | accepted | all |
| [DEC-20261016-branch-from-usman](DEC-20261016-branch-from-usman.md) | Umar Mid-I branch from `usman` | accepted | Umar |
| [DEC-20261016-usman-baseline](DEC-20261016-usman-baseline.md) | Accept Usman Mid-I baseline with open blockers | accepted | Umar (audit) |
| [DEC-20261016-docs-obsolete](DEC-20261016-docs-obsolete.md) | Move software/pitch docs to `docs/obsolete/` | accepted | Umar |
| [DEC-20261016-ci-branch-trigger](DEC-20261016-ci-branch-trigger.md) | CI push includes graph-diagnostics branch | accepted | Umar, Usman |

## Template for new decisions

Create `DEC-YYYYMMDD-short-slug.md` with: Status, Context, Decision, Consequences, Owners, Date. Add a row here.
