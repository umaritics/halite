---
id: dec-workspace-auth-rbac-postgresql
title: M01 Workspace Authentication, Invite-Only Onboarding, RBAC, and PostgreSQL Audit Trail
status: accepted
owners: [Umar, Usman, Shahmeer]
updated: 2026-11-14
---

# DEC-20261114 — Website Authentication, RBAC & PostgreSQL Identity Store (M01)

## Status

`accepted` (implements FYP-I Final Task 5 / Module M01 Workspace & Identity aligned with `Halite_FYP_Report.pdf` §8.3 & §8.5).

## Context

Following global API hardening (`DEC-20261114-public-api-security-hardening`), the hosted React website required interactive user authentication and role-based authorization so:
1. Public browser bundles no longer need to embed a static `VITE_HALITE_API_KEY` (`HALITE_API_KEY` stays strictly server-to-server).
2. Open public bot registration remains impossible (avoiding external Groq LLM quota abuse), while administrators can onboard teammates cleanly via single-use invitation links.
3. Conflict review actions (`Accept` / `Reject`) enforce role separation (`supervisor` / `admin` vs `technician`) and record reviewer identity in both the graph and an append-only relational audit log.
4. Per `Halite_FYP_Report.pdf` §8.5, transactional SaaS state (`organizations`, `users`, `user_sessions`, `user_invites`, `audit_events`) belongs in **PostgreSQL** rather than consuming Neo4j graph node budget.

## Decision

1. **Relational Identity Store (`backend/db/models.py`, `backend/db/session.py`):**
   - SQLAlchemy 2.0 store targeting PostgreSQL (`postgres:16-alpine` in `docker-compose.yml` and `docker-compose.vm.yml`, or any Supabase PostgreSQL URI via `DATABASE_URL`).
   - Falls back to isolated in-memory SQLite (`sqlite+pysqlite:///:memory:`) only when `DEMO_MODE=true` and `DATABASE_URL` is unset; fails closed (`503`) in non-demo mode if unconfigured.
2. **Argon2id + Short-Lived JWT + Rotating Refresh Token Families (`backend/services/auth_service.py`):**
   - Passwords hashed with `argon2-cffi` (Argon2id) with dummy-hash constant-time verification for unknown emails and 5-attempt account lockout (`429`).
   - 15-minute `HS256` Access JWT (`sub`, `sid`, `role`, `org_id`) verified cryptographically AND checked against active `User` + non-revoked `UserSession` rows so logout, role edits, and account deactivation take effect immediately.
   - 7-day single-use rotating refresh tokens stored only as SHA-256 hashes (`HttpOnly` cookie + JSON token for cross-origin Safari/Brave compatibility), with **token-family theft revocation** on replay.
3. **Invite-Only Onboarding & RBAC (`backend/api/routes/auth.py`, `backend/api/security.py`):**
   - Public self-signup is disabled. Administrators issue 72-hour single-use invites (`POST /api/admin/invites` -> `/accept-invite?token=...`).
   - Roles: `technician` (read fleet/graph, ingest, run diagnostics/Copilot), `supervisor` (+ adjudicate `/api/maintenance/review-queue/{id}/accept|reject`), `admin` (+ `/api/admin/*` user/invite/audit governance and batch analysis).
4. **Reviewer Provenance (`backend/api/routes/maintenance.py`, `AssetHistory.jsx`):**
   - `Accept` and `Reject` stamp `reviewed_by_id`, `reviewed_by_name`, `reviewed_by_email`, `reviewed_by_role`, and `reviewed_at` onto the `ServiceRecord` node and append `maintenance.review.accepted` / `maintenance.review.rejected` to `audit_events`.
5. **Frontend UX (`Login.jsx`, `AcceptInvite.jsx`, `TeamAccess.jsx`, `AuthContext.jsx`, `ProtectedRoute.jsx`):**
   - `/app/*` requires an authenticated user session (`/login` redirect with destination preservation); `VITE_HALITE_API_KEY` is removed from hosted Vercel browser builds.

## Consequences

- Satisfies SRS `FR-01`, `FR-02`, `FR-03` and FYP-I Final Task 5 ahead of schedule while preserving 100% of Neo4j Aura capacity for maintenance records.
- Ready for FYP-I Final Task 6 (server-side Copilot `diagnostic_sessions` table in the same PostgreSQL database) and optional Supabase Postgres migration via a single `DATABASE_URL` change.

## Owners

Umar, Usman, Shahmeer.
