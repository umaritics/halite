---
id: DEC-20261016-knowledge-rename
title: Rename docs/technical to knowledge/
status: accepted
owners: [Umar]
updated: 2026-10-16
---

# DEC-20261016 — knowledge/ location

## Context

The context bank lived under `docs/technical/`, mixed with PDFs and Mid-I evidence. Agents and humans need a top-level, purpose-built home.

## Decision

Move the bank to repo-root **`knowledge/`**. Keep university/report PDFs and Mid-I evidence under `docs/`. Root `AGENTS.md` remains the universal agent contract for non-Cursor tools.

## Consequences

All routers, Cursor rules, and decisions reference `knowledge/**`. `docs/technical/` no longer exists.
