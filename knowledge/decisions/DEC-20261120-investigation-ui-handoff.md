---
id: dec-investigation-ui-handoff
title: Prepare independent session features and review shared registration
status: proposed
owners: [Usman, Shahmeer]
updated: 2026-11-20
---

# Investigation UI registration handoff

## Status

Feature implementation is prepared by Usman. The user explicitly authorized
“Prepare the integration for review” in this chat. Shared-file changes are being
prepared on a separate review branch; Shahmeer's review is still required before
merge. No teammate signature or acceptance is implied by that user authorization.

## Context

The plan gives investigation/home features to Usman and the shell/auth context to
Shahmeer. His frontend registry preparation has not landed. Waiting for it would
prevent independent integration testing, while unilateral edits would obscure
ownership and review boundaries.

## Decision

Implement feature-owned manifests, API wrapper and pages with the existing design
classes/shared client. Verify them independently with real auth/API/databases in
a local preview harness, plus a separate feature build. Prepare a focused shared
registration/logout migration proposal with a generic manifest registry, shell
routes/nav and auth-default destinations. Keep that integration as a separate
reviewable change; do not merge/deploy it without the required cross-review.
Shahmeer's broader cleanup/client split/primitives/chart library remain his work.

## Consequences

Feature behavior can be tested before shared registration. The preview is never
reported as the production BrowserRouter. Production redirect/logout tests and
browser checks must execute on the integration branch before claiming WP-S3/S7/S9
end-to-end completion. Legacy browser copies are cleared, not imported, because
they carry no owner. Research policy/grounding remain separate work packages.

## Owners

Muhammad Usman Al Haq: feature files, tests and proposed integration.
Shahmeer Atif: shared shell/auth registration review and frontend preparation.

## Verification follow-up

The separate integration branch now applies the focused proposal and has passed
256 frontend tests, the main build and the real BrowserRouter workflow against
Neo4j/PostgreSQL. Global logout failure cleanup, direct routes/refresh and next
account isolation are included. User authorization permits preparation for review;
status remains proposed until Shahmeer review.
