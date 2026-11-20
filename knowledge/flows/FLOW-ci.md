---
id: flow-ci
title: CI and verification flow
status: active
owners: [Usman]
updated: 2026-11-20
---

# CI verification flow

1. Pull requests (and configured branch pushes) trigger `.github/workflows/ci.yml`.
2. Backend starts ephemeral Neo4j and PostgreSQL, installs declared development
   dependencies, runs Ruff runtime-error lint and pytest with terminal/XML coverage
   plus JUnit. Session contracts run against both SQLite and a private temporary
   PostgreSQL schema; graph contracts run against both memory and Neo4j.
3. Coverage and JUnit artifacts upload even if tests fail, so failures stay reviewable.
4. Frontend installs its lockfile dependencies, runs Vitest and builds production assets.
5. Docker smoke builds/starts Compose, verifies real graph/auth/corpus APIs using the
   synthetic fixture, checks frontend HTML, captures logs and tears down its volumes.

```mermaid
flowchart TB
  Change[Push / pull request] --> Workflow[ci.yml]
  Workflow --> Lint[Ruff runtime errors]
  Lint --> Tests[pytest + JUnit + terminal/XML coverage]
  Tests --> Artifacts[upload-artifact reports]
  Tests --> Neo4j[(ephemeral Neo4j)]
  Tests --> Postgres[(ephemeral PostgreSQL / private test schemas)]
  Workflow --> Frontend[Vitest + production build]
  Workflow --> Compose[Docker Compose smoke]
  Compose --> Verify[verify_mid1_runtime.py]
  Compose --> Logs[Capture service state / logs]
  Logs --> Cleanup[Remove disposable stack]
```

A configured workflow is not evidence of a successful remote run. Record the run
URL and terminal job results in the work log before claiming CI passed. Coverage
scope is explicit; the NFR-04 80% target is not satisfied by a report alone.
Staging deployment remains separate and main-only; no test targets shared data.
