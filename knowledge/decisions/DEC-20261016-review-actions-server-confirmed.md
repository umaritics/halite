---
id: DEC-20261016-review-actions-server-confirmed
title: Review Accept/Reject wait for the server; no bare-key shortcuts
status: accepted
owners: [Shahmeer]
updated: 2026-10-16
---

# DEC-20261016 — Review actions are server-confirmed

## Context

`POST .../accept` and `.../reject` change a record's `status` in Neo4j and cannot be undone from the UI. The page removed the
record and announced "Accepted" before the request finished, and a bare `A` key accepted the current record with no
confirmation. Mid-I rule: accept/reject state follows server confirmation; do not damage the demo corpus.

## Decision

- Update the queue and show the toast only after a successful response; on failure keep the record and show the server detail.
- Buttons lock while a request is pending.
- Remove `A`/`R` shortcuts; keep arrow-key navigation.
- State in the UI that neither action deletes the record.

## Consequences

- Do not click Accept/Reject on the shared staging corpus during demos; use seeded/test data.
- Optimistic updates or key shortcuts for these actions need a new DEC and a confirmation step.
- Tests: `ReviewQueue.test.jsx` (pending state, failure, note required, stray key).
