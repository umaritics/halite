# Research publication preserves measured evidence

- Status: implemented; product charts and owner integration review pending
- Date: 2026-11-20
- Owner: Usman

## Context

The plan requires product charts served through sessions/experiments. Existing
2024 results are selection evidence; no operating point is accepted.

## Decision

Publish exact committed results behind website-user authentication with a fixed
path allowlist and checksum manifest. Validate compatible methods, temporal split,
corpus and measurement semantics. Treat an explicit empty manifest as empty, but
missing or corrupt evidence as unavailable. Return private/no-store responses.

## Consequences

No generated fallback, inferred winner, invented operating point or held-out
performance enters the display. New accepted-policy/held-out publications need
a new explicit publication contract. The top-3 outcome proxy cannot be labelled
a measured sentence hallucination rate.
