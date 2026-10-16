---
id: DEC-20261016-context-bank
title: Adopt knowledge bank + agent protocol
status: accepted
owners: [all]
updated: 2026-10-16
---

# DEC-20261016 — Knowledge bank

## Context

Mid-I work spans three owners and many AI coding sessions. Knowledge was scattered across PDFs, mid1 evidence notes, and chat history, causing repeated rediscovery and scope drift.

## Decision

Maintain `knowledge/` as the durable project knowledge bank:

- `context/` — semantic + human rationale
- `decisions/` — short ADRs
- `flows/` — intended flows + Mermaid dependency graphs
- `INDEX.md` / `REGISTRY.md` / `README.md` — retrieval routers

Universal protocol for every agent/tool: root `AGENTS.md`. Cursor also enforces via `.cursor/rules/`.

## Consequences

- Slightly more PR overhead; much cheaper onboarding and safer Mid-I claims.
- Mid-I audit snapshots stay in `docs/mid1/`; lasting lessons get promoted into decisions/context.
- Obsolete product docs stay in `docs/obsolete/` and are not authoritative.
