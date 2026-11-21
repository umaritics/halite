# Remaining legacy retirement — concrete handoff proposal

Master-plan contracts §3.1 asks Usman to remove the software domain. The compatible
foundation deliberately deferred that behavior change; this proposal makes the
remaining contract and shared-file dependencies explicit. No retirement change
has been applied to runtime files by this dependency-only branch.

## Exact owner integration patch

`LEGACY_RETIREMENT_HANDOFF.patch` applies cleanly to the current tree (verified
with `git apply --check`). It changes only:

1. `backend/agents/maintenance_agent.py`: stop inheriting the retired generic
   `BaseAgent`; provide the same constructor arguments and two stored attributes
   directly on MaintenanceAgent. No ingest, parsing, deduplication or graph logic changes.
2. `backend/domains/registry.py`: remove the SoftwareDomainAdapter import/entry
   and make maintenance the sole/default descriptor. Unknown domains still fail.

These are Shahmeer's vertical-owned files under the master plan. AGENTS.md says
“do not edit another owner’s files without a handoff decision”; owner review and
merge are required even after Usman authorizes preparation/testing.

## Proposed retirement scope after handoff

- Delete owned legacy routers: `backend/api/routes/{chat,decisions,ingest,alerts,webhooks}.py`.
- Unregister those routers from `api/router.py`; keep graph overview, all existing
  graph/reset safety boundaries, maintenance, diagnostics, auth, ops and vertical APIs.
- Delete `backend/agents/{code,document,decision,gitea,base}_agent.py`,
  `backend/services/context_builder.py`, `backend/domains/software.py`,
  `backend/graph/invalidation.py` and the root-level ad-hoc scripts named in the plan.
- Remove automatic software/demo seeding from every production startup branch;
  keep explicit test fixture seeding and the existing ops-protected manual reset
  contract until its owner decides otherwise. Do not purge existing graph data.
- Remove `tests/test_regression_software.py` as explicitly named by the plan.
  Replace obsolete security-route expectations with route-absence assertions;
  retain auth/rate-limit coverage by exercising current maintenance endpoints.
- Update only software-domain expectations in `test_api_maintenance.py` to the
  sole/default maintenance descriptor. Preserve every maintenance behavioral test.
- Preserve graph mixin method compatibility and `/api/graph/overview`; no schema,
  retrieval, integrity, frontend shell or staging changes.

## Reviewable HTTP changes

| Surface | Before | Proposed after retirement |
| --- | --- | --- |
| `/api/chat`, `/api/decisions*`, `/api/ingest*`, `/api/alerts*` | Software functionality or retired integration | Unregistered: 404, absent from OpenAPI |
| `/api/webhook/gitea` | 410 by default; optional signed processing | Unregistered: 404 even if old enable flag is supplied |
| `/api/domains` and health `domains` | Software + maintenance; software default | Maintenance only, default=true |
| Startup software demo records | Seeded into memory and live Neo4j | No automatic software seeding |
| `/api/maintenance/*`, auth and graph reset | Existing contracts | Preserve behavior/security, verify hosted tests |

## Verification required before review handoff

Full hosted lint/tests/build and disposable Neo4j/Postgres/API/browser flows;
explicit route-absence/default-domain/startup checks; dependency/import audit and
coverage report. No tests run against staging or real user data. No real graph
reset, data purge or deployment is authorized by this proposal.

The current independent dependency cleanup removes unused direct requirements
without applying this retirement. Pandas, docx2txt and pypdf remain where actual
code still imports them; dotenv remains transitively required.

## User handoff authorization — 21 November 2026

The user explicitly answered **“Prepare and test retirement for review”** after
being shown the two shared-file dependencies and HTTP contract changes. This
authorizes applying/testing the proposed retirement on a separate review branch.
It does not represent Shahmeer/Umar review, merge approval or staging deployment.
Do not request this preparation authorization again.

## Implementation branch update

`codex/usman-legacy-retirement` applies the authorized two-file patch and full
retirement above. Removed document parsers pypdf/docx2txt now have no consumers.
New retirement tests verify route absence under both obsolete flag settings and
both auth states, no graph/model side effects, and actual startup lifecycle
without software seeding in all three graph branches. Existing maintenance,
graph reset, authentication and rate-limit coverage is retained. Hosted results
and owner review are pending; this does not claim deployment.
