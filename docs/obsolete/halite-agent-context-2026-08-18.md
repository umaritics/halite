# Halite Agent Context

This file is an exported project-memory snapshot for IDE agents.
Use it to narrow code exploration, then verify the minimum necessary files.

## Working rules
- Prefer cited file paths over broad repository scans.
- Treat decisions with status `needs_review` or `invalidated` as risky.
- Verify the referenced files before making code changes.

## Components

### Alerts
- Type: module
- File: N/A
- Description: No description recorded.
- Decisions:
  - Event-Driven Architecture for Decision Invalidation [active]
    - Why it exists: When a commit modifies a component file, we publish an event so Alerts can flag related decisions without blocking the ingest pipeline, decoupling Gitea sync from the UI.
    - Source: document (sample_meeting_transcript.txt)

### ApiGateway
- Type: module
- File: N/A
- Description: No description recorded.
- Decisions:
  - External Traffic Routing via ApiGateway [active]
    - Why it exists: Centralizes auth checks, rate limiting, and routing to internal services.
    - Source: document (sample_meeting_transcript.txt)

### auth.service
- Type: module
- File: src/auth/auth.service.ts
- Description: Inferred from commit touching src/auth/auth.service.ts
- Decisions: none linked

### AuthModule
- Type: module
- File: N/A
- Description: No description recorded.
- Decisions:
  - Auth token strategy: JWT vs sessions [active]
    - Why it exists: The client needs a mobile app with offline‑capable auth tokens, and stateless tokens simplify horizontal scaling of AuthModule.
    - Source: document (sample_meeting_transcript.txt)
  - External Traffic Routing via ApiGateway [active]
    - Why it exists: Centralizes auth checks, rate limiting, and routing to internal services.
    - Source: document (sample_meeting_transcript.txt)

### DatabaseLayer
- Type: module
- File: N/A
- Description: No description recorded.
- Decisions:
  - Database choice: PostgreSQL vs MongoDB [active]
    - Why it exists: Relational data with strict ACID requirements for billing and user accounts; PostgreSQL offers mature tooling and JSON columns for flexibility.
    - Source: document (sample_meeting_transcript.txt)

### Decision Invalidation
- Type: module
- File: N/A
- Description: No description recorded.
- Decisions:
  - Event-Driven Architecture for Decision Invalidation [active]
    - Why it exists: When a commit modifies a component file, we publish an event so Alerts can flag related decisions without blocking the ingest pipeline, decoupling Gitea sync from the UI.
    - Source: document (sample_meeting_transcript.txt)

### gateway
- Type: module
- File: src/api/gateway.ts
- Description: Inferred from commit touching src/api/gateway.ts
- Decisions: none linked

### Gitea sync
- Type: module
- File: N/A
- Description: No description recorded.
- Decisions:
  - Event-Driven Architecture for Decision Invalidation [active]
    - Why it exists: When a commit modifies a component file, we publish an event so Alerts can flag related decisions without blocking the ingest pipeline, decoupling Gitea sync from the UI.
    - Source: document (sample_meeting_transcript.txt)

### postgres
- Type: module
- File: src/db/postgres.ts
- Description: Inferred from commit touching src/db/postgres.ts
- Decisions: none linked

### README
- Type: module
- File: README.md
- Description: Inferred from commit touching README.md
- Decisions: none linked

### UI
- Type: module
- File: N/A
- Description: No description recorded.
- Decisions:
  - Event-Driven Architecture for Decision Invalidation [active]
    - Why it exists: When a commit modifies a component file, we publish an event so Alerts can flag related decisions without blocking the ingest pipeline, decoupling Gitea sync from the UI.
    - Source: document (sample_meeting_transcript.txt)
