# Retire the software surface without purging existing graph data

- Status: implemented and hosted verified on 5817fd9; owner review/merge pending
- Date: 2026-11-21
- Owners: Usman; Shahmeer owner review required for importer/domain integration

## Context

Master-plan contracts §3.1 explicitly removes the old software domain. The user
answered “Prepare and test retirement for review” after receiving the exact
shared-file patch and HTTP changes. This permits preparation/testing; it does
not constitute teammate approval, merge or deployment.

## Decision

Delete all named legacy software routers/agents/context/domain/invalidation,
root ad-hoc scripts and software regression suite. Unregister old endpoints,
including Gitea irrespective of obsolete enable flags. Maintenance is the sole
and default domain. MaintenanceAgent keeps the same constructor directly and
unchanged ingestion methods. Remove every automatic demo seed call in startup.
Remove now-unused pypdf/docx2txt dependencies and audit their absence.

## Consequences

Retired endpoints return 404 and disappear from OpenAPI. Auth/rate-limit tests
exercise maintained endpoints. Real production lifespan tests cover memory,
connected Neo4j adapter and failed-connect fallback, with forbidden seed hooks.
Existing graph data is not deleted. Existing graph endpoints/reset guards and
legacy graph mixins remain compatible, including explicit test/manual seeds.
The Neo4j lifecycle unit adapter is synthetic; actual graph operation is checked
separately by hosted disposable Neo4j tests and full-stack smoke. Staging is not
modified. Owner review/merge remain explicit gates.

Run 44882037412 passed 440 backend/279 frontend tests and full live disposable
Neo4j/Postgres/browser smoke. Exact broad coverage 79.58% remains below 80%;
see LEGACY_RETIREMENT_VERIFICATION.md and phase13 proof.
