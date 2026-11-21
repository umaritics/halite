---
id: dec-backend-foundation
title: Preserve contracts while separating backend verticals
status: accepted
owners: [Usman]
updated: 2026-11-20
---

# Backend foundation and model output formats

## Status

Accepted for the compatibility-preserving foundation; no cross-owner contract change approved here.

## Context

The master plan assigns Usman backend preparation. Existing consumers import
`graph.queries.GraphRepository`, `graph.memory_store.MemoryGraphStore` and
`db.models`. The plan also asks to retire software while retaining unchanged
maintenance tests, but those tests explicitly assert software registration/default.
The graph and retired Gitea/security contracts also retain legacy consumers.

## Decision

Split implementations into `graph/repo/` and `graph/memory/`, with `core`,
`retrieval`, `integrity` mixins and an isolated `legacy` mixin. Retain compatibility
imports and every existing method body/signature. Keep legacy registration and
seeding for this phase; retirement requires a separate explicit contract change
with affected tests updated. This phase completes WP-S0 steps 2–5, not all WP-S0.

Move identity models verbatim into `db/models/identity.py`; re-export their public
names and import the three vertical extension modules from the package registry.
Do not create speculative tables or alter existing columns. Register four
vertical routers under the authenticated parent. Empty summary statistics are
intentional until vertical owners provide measured data.

Add `json_mode=False` to model chat APIs. Only JSON extraction or explicit JSON
calls request `response_format`, for both Groq and the local compatible provider.
Propagate the choice through usage accounting and provider-key retries.

## Consequences

Existing callers and maintenance/security tests remain compatible. Each owner
has dedicated query/model/router extension points. No schema migration or live
staging write is needed. Legacy retirement and full WP-S1 remain tracked work.
No research thresholds, labels, FAA meanings or model choice are decided here.

## Owners

Usman (backend preparation and model adapter). Retrieval mixins: Umar; integrity
mixins: Shahmeer. Shared core remains stewarded by Usman.
