---
id: DEC-20261016-docs-obsolete
title: Obsolete software/pitch documentation
status: accepted
owners: [Umar]
updated: 2026-10-16
---

# DEC-20261016 — docs/obsolete

## Context

Product scope shifted from software-decision vault to maintenance diagnostics. Pitch/proposal/agent-context benchmark docs create false context for agents.

## Decision

Keep authoritative Mid-I + maintenance technical docs active. Move software-domain proposals, pitch decks, agent-context benchmarks, and similar material to `docs/obsolete/`. Delete `demo-app/` software scaffold. Keep brand assets and FYP handbook/guides.

## Consequences

Agents must not treat `docs/obsolete/**` as current requirements. Prefer `knowledge/**` and the three Mid-I PDFs.
