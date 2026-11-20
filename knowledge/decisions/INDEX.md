---
id: decisions-index
title: Architecture / process decisions
status: active
owners: [all]
updated: 2026-11-20
---

# Decisions index

Newest first. Status: `accepted` | `proposed` | `superseded`.

| ID | Title | Status | Owners |
| --- | --- | --- | --- |
| [DEC-20261120-portable-model-comparison](DEC-20261120-portable-model-comparison.md) | Fixed real prompts, portable measured comparison and explicit M4 provenance | implemented / measurements pending | Usman |
| [DEC-20261120-grounding-human-calibration](DEC-20261120-grounding-human-calibration.md) | Saved audits, explicit calibration and blinded independent human review | implemented / calibration pending | Usman |
| [DEC-20261120-responsive-shell-review](DEC-20261120-responsive-shell-review.md) | User-authorized responsive App/Sidebar preparation with measured phone usability | proposed / review pending | Usman, Shahmeer |
| [DEC-20261120-managed-question-snapshots](DEC-20261120-managed-question-snapshots.md) | Saved question IDs, graph/model-independent answers and explicit activation | implemented / selection pending | Usman |
| [DEC-20261120-decision-core-protocol](DEC-20261120-decision-core-protocol.md) | Uncalibrated runtime beliefs and temporally isolated selection | accepted | Usman |
| [DEC-20261120-investigation-ui-handoff](DEC-20261120-investigation-ui-handoff.md) | Independent investigation UI and separately reviewed shared registration | proposed | Usman, Shahmeer |
| [DEC-20261120-durable-investigations](DEC-20261120-durable-investigations.md) | User-owned atomic session turns, replay and opt-in degraded diagnosis | accepted | Usman |
| [DEC-20261120-backend-foundation](DEC-20261120-backend-foundation.md) | Compatible vertical backend packages and explicit model JSON mode | accepted | Usman |
| [DEC-20261120-vertical-ownership](DEC-20261120-vertical-ownership.md) | Ownership moves from layers to three full-stack verticals | accepted | Umar, Usman, Shahmeer |
| [DEC-20261116-staging-corpus-analysis-complete](DEC-20261116-staging-corpus-analysis-complete.md) | Staging full-corpus conflict analysis complete (0 unscored) | accepted | Umar, Usman |
| [DEC-20261115-local-ollama-staging](DEC-20261115-local-ollama-staging.md) | Private Ollama on staging for unbounded conflict classification | accepted | Umar, Usman |
| [DEC-20261114-workspace-auth-rbac-postgresql](DEC-20261114-workspace-auth-rbac-postgresql.md) | M01 Workspace Authentication, Invite-Only Onboarding, RBAC, and PostgreSQL Audit Trail | accepted | Umar, Usman, Shahmeer |
| [DEC-20261114-public-api-security-hardening](DEC-20261114-public-api-security-hardening.md) | Global API key authentication, fail-closed startup, Gitea retirement, and container sandboxing | accepted | Umar, Usman, Shahmeer |
| [DEC-20261025-evidence-provenance](DEC-20261025-evidence-provenance.md) | Consolidate diagnostic evidence without altering retrieval semantics | accepted | Umar, Shahmeer |
| [DEC-20261017-analysis-cost-cascade](DEC-20261017-analysis-cost-cascade.md) | Pre-register the opt-in conflict-analysis cost cascade | accepted | Umar, Usman, Shahmeer |
| [DEC-20261017-conflict-analysis-state](DEC-20261017-conflict-analysis-state.md) | Persist honest conflict-analysis state separately from confidence | accepted | Umar, Usman, Shahmeer |
| [DEC-20261017-fleet-service-records](DEC-20261017-fleet-service-records.md) | Fleet-wide paginated Service Records and corrections | accepted | Umar, Usman, Shahmeer |
| [DEC-20261017-graph-aircraft-focus](DEC-20261017-graph-aircraft-focus.md) | Knowledge Graph shows one aircraft's stored subgraph with truthful counts | accepted | Shahmeer |
| [DEC-20261018-protect-graph-reset](DEC-20261018-protect-graph-reset.md) | Graph reset needs the operations token (and a typed confirmation for Neo4j) | accepted | Usman, Umar, Shahmeer |
| [DEC-20261017-ingest-csv-upload-ui](DEC-20261017-ingest-csv-upload-ui.md) | Ingest page uploads a CSV via the existing upload route; honest counts, inline errors | accepted | Shahmeer |
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
| [DEC-20261120-question-selection-protocol](DEC-20261120-question-selection-protocol.md) | Official codes, temporal likelihoods, three controls and authorized shared-field review preparation | offline implemented / integration review pending | Usman, Shahmeer |

## Template for new decisions

Create `DEC-YYYYMMDD-short-slug.md` with: Status, Context, Decision, Consequences, Owners, Date. Add a row here.
