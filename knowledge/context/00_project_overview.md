---
id: ctx-overview
title: Project overview (Mid-I lens)
status: active
owners: [all]
updated: 2026-10-16
depends_on: []
---

# Project overview

**Halite** is an AI-powered maintenance diagnostics and asset intelligence platform. Mid-I target: one **working vertical slice**, not 20% of every future module.

## What Mid-I must show

A technician can: pick a real asset → inspect dated `ServiceRecord` history → enter a symptom → get graph-grounded ranked investigative checks with citations → open a cited record → see at least one conflict/review example → show CI/tests evidence. Failures (unknown asset, no LLM, empty history) must be honest, not invented.

## Milestone framing (`halite_timeline.pdf`)

| Gate | Intent |
| --- | --- |
| FYP I Mid (~20%) | Working diagnostic foundation + existing conflict capability + CI |
| FYP I Final (~50%) | Integrated MVP (hybrid retrieval, sessions, RBAC, eval suite…) |
| FYP II | Training, analytics, SaaS hardening, evaluation, defense |

## Product pillars (report)

Knowledge graph over FAA SDR-style records; diagnostic ranking with citation validation; conflict detection + human review; later: training, fleet analytics, multi-tenant SaaS.

## Related

- Scope/deferred: [01_domain_scope_deferred.md](01_domain_scope_deferred.md)
- Ownership: [02_ownership_mid1.md](02_ownership_mid1.md)
- Architecture: [03_architecture.md](03_architecture.md)
