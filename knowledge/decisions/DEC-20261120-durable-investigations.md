---
id: dec-durable-investigations
title: User-owned atomic investigation turns and explicit degraded mode
status: accepted
owners: [Usman]
updated: 2026-11-20
---

# Durable investigation sessions

## Status

Accepted implementation of the master plan's WP-S2 and backend WP-S1 boundaries.
No research operating point, labels, FAA meanings or interactive model is chosen.

## Context

The browser-only Copilot cannot provide cross-client history, ownership or replay.
Multiple requests and a close operation can race while a slow model is answering.
The old diagnose cache has no evidence revision and can accept citations to reports
not shown in its prompt. The plan requires preserving existing response fields.

## Decision

Add three tables under the pre-registered sessions model module, without altering
identity tables. Store the complete response/evidence on the turn in addition to
the planned hypothesis/evidence-ID snapshot. Persist `turn_count` on the session
as an optimistic concurrency revision. Inference runs outside a SQL transaction;
a conditional open/revision update, turn and snapshot commit together. A stale
turn gets 409; a persistence failure rolls back everything. This works across
multiple processes and both PostgreSQL and SQLite without process-local locks.

Derive visibility from the verified user/organisation. Service principals cannot
impersonate a session owner. Supervisors can read others' sessions but cannot
write them. Server state is authoritative; client state replacement is ignored.

Session outages get a deterministic ranking-derived reply. Keep stateless Copilot
outage fields unchanged. Quick diagnosis supports an additive opt-in degraded
response and retains its default 503. Cache keys include content, count, mode and
prompt version; reject empty/corrupt cache payloads. Validate diagnose citations
against exactly the bounded IDs shown in the prompt.

Do not fabricate a decision policy to populate new fields: explicitly abstain
with `policy_status=not_configured` until the measured policy is implemented.
The printable closed-session report escapes all values and inherits read access.

## Consequences

Saved sessions survive browser/app changes and remain replayable after graph
updates. Competing expensive requests can perform work that is discarded with
409; the database stays correct. Session/outcome tables are additive and can be
created by the existing model registry. No staging migration is performed here.
Full policy, questions, grounding and frontend history remain subsequent work.

## Owners

Muhammad Usman Al Haq, Investigation Sessions. Identity/authentication is consumed
unchanged; retrieval and integrity remain owned by their respective verticals.
