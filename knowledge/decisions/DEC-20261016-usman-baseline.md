---
id: DEC-20261016-usman-baseline
title: Usman Mid-I baseline cross-check
status: accepted
owners: [Umar]
updated: 2026-10-16
---

# DEC-20261016 — Usman baseline cross-check

## Context

Before Umar Mid-I work, verify Usman’s A1–A4 against `halite_work_division_mid1.pdf`, using his evidence on `usman` (`docs/mid1/05_usman_final_audit.md`, `07_usman_release_readiness.md`, CI, setup guides).

## Decision (audit summary)

| Package | Required | Observed on `usman` tip | Verdict |
| --- | --- | --- | --- |
| **A1** Data/env | Real Neo4j + corpus, health honest, idempotent ingest | Synthetic Docker smoke PASS; real FAA in running Neo4j **BLOCKED** on Usman host; CSV file facts documented | **Partial / blocked** — fair; infra-dependent |
| **A2** Maintenance APIs + conflict | Assets/history/review/accept-reject tested | 59/59 owned tests; full backend suite green in CI-equivalent mode | **PASS** — meets owned scope |
| **A3** GitHub Actions + health | CI fails on red tests; meaningful jobs | Workflow exists; backend+docker green; **frontend job red**; no full CD; VM stale (no maintenance routes) | **Partial** — CI scaffold good; merge gate not green |
| **A4** Wiring + docs | Routers, setup/test evidence docs | `main.py` registers routes; `mid1_setup.md` / evidence docs present; live Groq diagnostic **NOT VERIFIED** (handed to Umar) | **Partial** — docs/wiring OK; live model open |

**Overall:** Usman’s owned core (A2 + CI/Docker scaffolding + docs) is in good shape and is a valid base. He correctly **did not claim** merge readiness. Remaining blockers are cross-owner (Shahmeer frontend test, infra for real corpus, Umar live diagnose proof, deploy admin).

## Consequences for Umar

1. Do not “fix” Shahmeer frontend CI unless explicitly handed off — stay in graph/diagnostics ownership.
2. Own live-model diagnose verification and citation/ranker honesty (U1–U5 + Usman’s live-model checklist).
3. Prefer synthetic+local Neo4j when available; keep claims aligned with `/api/health`.
4. Treat Usman docs under `docs/mid1/` as evidence snapshots; promote durable facts into this bank.
