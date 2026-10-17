---
id: flow-ci
title: CI / verification flow
status: active
owners: [Usman]
updated: 2026-10-16
---

# FLOW-ci — GitHub Actions gates

## Jobs

1. **backend** — pytest with `DEMO_MODE=true`, empty Groq secrets, and an
   ephemeral Neo4j 5 service so repository contracts execute in both stores.
2. **frontend** — `npm ci`, `npm test`, `npm run build`.
3. **docker-smoke** — compose up, health, `verify_mid1_runtime.py`, frontend root HTML check, teardown.

## Dependency graph

```mermaid
flowchart TB
  Push[push / pull_request] --> WF[.github/workflows/ci.yml]
  WF --> B[backend pytest]
  WF --> F[frontend test+build]
  WF --> D[docker compose smoke]
  D --> V[verify_mid1_runtime.py]
  D --> N[(ephemeral Neo4j)]
```

## Mid-I evidence note

Usman audit: backend + docker jobs green; frontend job red (Shahmeer mock). Overall workflow must be green before merge claims.
