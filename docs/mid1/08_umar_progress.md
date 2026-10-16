# Umar Mid-I progress log

Owner: Muhammad Umar (23I-0782)  
Branch: `umar/mid1-graph-diagnostics`  
Last updated: 2026-10-16  
Baseline: branched from `usman` @ `b949de4` via `feat/mid1/graph-diagnostics` @ `30b322b` (staging CD)

## Done

| Item | Evidence / notes |
| --- | --- |
| Branched from Usman Mid-I DevOps tip | `umar/mid1-graph-diagnostics` (from `feat/mid1/graph-diagnostics`) |
| Usman A1–A4 cross-check | `knowledge/decisions/DEC-20261016-usman-baseline.md` — A2 pass; A1/A3/A4 partial with open blockers |
| Knowledge bank + `AGENTS.md` + Cursor rules | `knowledge/**`, root `AGENTS.md` |
| Docs cleanup → `docs/obsolete/` | Software/pitch docs archived |
| **U1** diagnostics audit | `knowledge/context/modules/diagnostics_u1_audit.md` — 20/20 retrieval tests; Jaccard + part_name ranker (not embeddings) |
| Shared staging API on VM | `https://dev1.corp.curatech.pk/halite-api` — Mid-I routes live |
| Corpus on staging | **2079** records (`maintenance_corpus_loaded=true`) |
| GitHub Actions CD | `Deploy staging backend` green on `30b322b` |
| Ops visibility for partners | `GET /api/ops/version` (public), `GET /api/ops/logs` (`X-Ops-Token`) |
| Dedicated deploy SSH key | GitHub secret `VM_SSH_KEY` — not personal SSH key |

## In progress / next (Umar)

| Package | Status | Next action |
| --- | --- | --- |
| **U2** Real-data graph retrieval | Next | Prove diagnose/history on staging Neo4j; bounded queries; unknown asset / empty history controlled |
| **U3** Deterministic ranking | Pending | Stable tie-break; document weights; evidence per candidate |
| **U4** Citation validation / LLM boundary | Pending | Real FAA ID tests; 503 when no Groq/cache; no invented IDs |
| **U5** Diagnostic backend tests + handoff | Pending | Route tests + fixtures for Shahmeer |

## Open for other partners (agents: read this)

### Shahmeer

1. Fix frontend CI failure from Usman handoff: `docs/mid1/06_frontend_review_queue_handoff.md` (`getRecord` mock).  
2. Ensure local `npm run dev` uses shared API — see `09_frontend_shared_api.md` (versioned `.env.development`).  
3. Wire Diagnostics UI to live `POST /api/maintenance/diagnose` against staging; show loading/empty/503 honestly.  
4. Evidence click-through from `ranked_checks` → record/history views.

### Usman

1. A1 real-corpus isolated runtime was previously blocked locally; staging now has corpus — reconcile evidence if needed.  
2. Keep CD secrets/environment healthy (`staging` env + `VM_SSH_*`).  
3. Own conflict/review path; do not change diagnose route internals without Umar.

## How partners use staging (no VM SSH)

- API base: `https://dev1.corp.curatech.pk/halite-api`  
- Health: `/api/health` — check `git_sha`, `graph_mode`, `llm_mode`, corpus count  
- Version: `/api/ops/version`  
- Logs: `/api/ops/logs` with `X-Ops-Token` (ask Umar/admin via password manager — **not in git**)  
- Backend updates: push to allowed branches → Actions **Deploy staging backend**

## Demo asset (staging)

Prefer a dense asset from the loaded corpus (historically `813SK`). Always confirm via `/api/maintenance/assets` before demo — do not hardcode if missing.
