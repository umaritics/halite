# Umar Mid-I final verification, evidence, and partner closure

Audit date: 2026-10-16  
Owner: Muhammad Umar (23I-0782)  
Branch: `umar/mid1-graph-diagnostics`  
Tip SHA (this document): `a70652ed67f44850f039a1a6db6852ba9a52fb0f`  
Branched from: `usman` @ `b949de4` (early tip briefly named `feat/mid1/graph-diagnostics` @ `30b322b`, then renamed/superseded by this branch)  
`origin/main` baseline (unchanged): `4329556c2405ffa1a397979ae26bc68ad8814eac`  
Staging public API: `https://dev1.corp.curatech.pk/halite-api`  
Usman baseline cross-check: [`knowledge/decisions/DEC-20261016-usman-baseline.md`](../../knowledge/decisions/DEC-20261016-usman-baseline.md)

## Executive verdict

**Umar-owned Mid-I packages U1–U5 are complete on this branch** with local tests, staging live-corpus proof, CD/ops unblocking, and partner handoffs.  
**Team Mid-I is not merge-ready:** Shahmeer frontend CI + assets N+1 UX remain open; Usman must reconcile A1 evidence against the now-live staging corpus; independent review pending. Do not merge to `main` from this document alone.

| Work package | Verdict | Reason |
| --- | --- | --- |
| **U1** Diagnostics audit | **PASS** | Inventory + method honesty recorded; retrieval unit tests green |
| **U2** Real-data graph retrieval | **PASS** | Staging Neo4j corpus 2079; history/diagnose/404 paths proven; Cypher LIMIT bounds landed |
| **U3** Deterministic ranking | **PASS** | `rank_diagnostic_checks` with documented weights + stable tie-break + unit tests |
| **U4** Citation / LLM boundary | **PASS** | FAA-shaped validation module; inventeds flagged; diagnose **503** without live Groq (tests + staging live path) |
| **U5** Diagnostic backend tests + handoff | **PASS** | Route + citation tests; Diagnostics UI contract frozen for Shahmeer |
| Staging / CD (Umar unblock) | **PASS** | Shared VM serves Mid-I maintenance+diagnose; Actions deploy from this branch |
| Team merge readiness | **NOT READY** | Frontend job historically red; assets list N+1; reviewer pending |

## Knowledge bank (agents must open these)

| Topic | Path |
| --- | --- |
| Router | [`knowledge/README.md`](../../knowledge/README.md) |
| Diagnostics module | [`knowledge/context/modules/diagnostics.md`](../../knowledge/context/modules/diagnostics.md) |
| U1 technical inventory | [`knowledge/context/modules/diagnostics_u1_audit.md`](../../knowledge/context/modules/diagnostics_u1_audit.md) |
| Diagnose flow | [`knowledge/flows/FLOW-diagnose.md`](../../knowledge/flows/FLOW-diagnose.md) |
| Deploy / staging | [`knowledge/context/modules/remote_backend.md`](../../knowledge/context/modules/remote_backend.md), [`knowledge/flows/FLOW-deploy.md`](../../knowledge/flows/FLOW-deploy.md) |
| Ownership | [`knowledge/context/02_ownership_mid1.md`](../../knowledge/context/02_ownership_mid1.md) |
| Registry | [`knowledge/REGISTRY.md`](../../knowledge/REGISTRY.md) |
| Agent contract | [`AGENTS.md`](../../AGENTS.md) |

## Package evidence index (detailed docs)

| Package | Detailed evidence |
| --- | --- |
| U1 | Knowledge: `diagnostics_u1_audit.md` (this audit supersedes stale “U2/U5 follow-up” caveats where noted below) |
| U2 | [`11_u2_real_data_retrieval.md`](11_u2_real_data_retrieval.md) |
| U3 | [`13_u3_deterministic_ranking.md`](13_u3_deterministic_ranking.md) |
| U4 + U5 | [`12_u4_u5_diagnostics_handoff.md`](12_u4_u5_diagnostics_handoff.md) |
| Frontend → staging | [`09_frontend_shared_api.md`](09_frontend_shared_api.md) |
| Perf (not Umar fix) | [`10_perf_assets_api_handoff.md`](10_perf_assets_api_handoff.md) |

## Git and ownership snapshot

| ID | Command / reference | Environment | SHA | Observed | Status | Remaining |
| --- | --- | --- | --- | --- | --- | --- |
| GIT-1 | `git rev-parse HEAD`; branch `umar/mid1-graph-diagnostics` tracks origin | Windows host | `a70652e` | Tip pushed; CD/CI branch list includes `umar/mid1-graph-diagnostics` | PASS | Keep work on this branch; no merge to `main` |
| GIT-2 | Diff vs Usman tip `b949de4` | Windows host | tip | Umar commits: CD/ops/knowledge (`30b322b`), mid1 docs+env (`0f471b5`), U2 (`408d1c4`), U3 (`e8093cb`), U4/U5 (`a70652e`) | PASS | Cross-owner frontend files not edited for perf fix |
| GIT-3 | `origin/main` | Windows host | `4329556` | Unchanged | PASS | Release coordinator only |

### Umar commits on this line (newest first)

| Commit | Scope |
| --- | --- |
| `a70652e` | U4 citation module + U5 diagnose API tests + handoff doc |
| `e8093cb` | U3 `rank_diagnostic_checks` + stable tie-break |
| `408d1c4` | U2 bounded Neo4j retrieval + staging proof doc |
| `0f471b5` | Mid-I progress/perf/shared-API docs; `.env.development`; CI/CD branch trigger |
| `30b322b` | Shared staging CD, ops API, knowledge bank (ancestor commit) |

## U1 — Diagnostics audit

| ID | File/reference | Exact command | Observed | Status |
| --- | --- | --- | --- | --- |
| U1.1 | `diagnostic_retrieval.py`, `diagnostics.py` | Source inventory in knowledge U1 note | Jaccard lexical similarity; part_name ranker; no embeddings | PASS |
| U1.2 | `tests/test_diagnostic_retrieval.py` | `python -m pytest -q tests/test_diagnostic_retrieval.py` (early U1) | 20 passed (memory store) | PASS |
| U1.3 | Honesty labels | Knowledge bank | Must not report conflict F1 as diagnostic accuracy; scores not probabilities | PASS |

**Problems found in U1 (and where resolved):**

| Problem | Severity | Resolution |
| --- | --- | --- |
| Fleet scan loaded all records unbounded | Medium (POC OK) | U2: `FLEET_SCAN_CAP=2500` + Cypher LIMIT |
| Asset history fetched 200 then truncated | Medium | U2: `list_asset_history_recent` DESC LIMIT |
| Rank tie-break score-only | Medium | U3: score → evidence_count → part_name |
| Citation regex untested on real FAA IDs | High for demo honesty | U4: module + SWIA/AALA tests |
| No diagnose route tests / no live staging proof | High | U2 staging + U5 API tests |

## U2 — Real-data graph retrieval

Full tables, Neo4j counts, and staging timings: [`11_u2_real_data_retrieval.md`](11_u2_real_data_retrieval.md).

| ID | Check | Result | Status |
| --- | --- | --- | --- |
| U2.1 | Neo4j Asset/ServiceRecord counts (MCP / Aura) | 118 assets, ~2078 links, max history 153 (`813SK`) | PASS |
| U2.2 | Staging `GET /api/health` | `graph_mode=neo4j`, `llm_mode=live`, corpus **2079** | PASS |
| U2.3 | `GET .../assets/{813SK UUID}/history` | 200, count=153, ~1.0s | PASS |
| U2.4 | Unknown asset history | HTTP **404** | PASS |
| U2.5 | `POST .../diagnose` live | 200; ranked_checks=10; cite `all_valid=true`; ~16s wall | PASS |
| U2.6 | Diagnose empty/missing asset | HTTP **404** | PASS |
| U2.7 | Bounded queries in code | recent history LIMIT; fleet LIMIT; batch outcomes | PASS |

This closes Usman’s A4.4 live-model gap **for staging** (sanitized: no keys logged; HTTP/schema/citation counts recorded in U2 doc).

## U3 — Deterministic ranking

Full weight table + tests: [`13_u3_deterministic_ranking.md`](13_u3_deterministic_ranking.md).

| ID | Check | Result | Status |
| --- | --- | --- | --- |
| U3.1 | Ranking pure graph (no LLM) | `rank_diagnostic_checks` in `diagnostic_retrieval.py` | PASS |
| U3.2 | Documented weights | `RANK_WEIGHT_ASSET_HISTORY=0.4`, fleet `0.6`, superseded `0.3` | PASS |
| U3.3 | Stable tie-break | score DESC, evidence_count DESC, part_name ASC; IDs/sources sorted | PASS |
| U3.4 | Unit tests | tie-break, blank skip, deterministic re-run | PASS |

## U4 — Citation validation / LLM boundary

Full contract + tests: [`12_u4_u5_diagnostics_handoff.md`](12_u4_u5_diagnostics_handoff.md).

| ID | Check | Result | Status |
| --- | --- | --- | --- |
| U4.1 | Module | `backend/services/citation_validation.py` | PASS |
| U4.2 | Real FAA shapes | `SWIA2025091876593`, `AALA202504075792` extracted | PASS |
| U4.3 | Invented ID | → `invalid_ids` + `[UNVERIFIED:…]` in explanation | PASS |
| U4.4 | No live Groq | diagnose HTTP **503** (`test_api_diagnostics`) | PASS |
| U4.5 | Staging live path | diagnose 200 with `citation_validation.all_valid=true` (U2 proof) | PASS |

## U5 — Backend tests + Shahmeer handoff

| ID | Module | Command / note | Status |
| --- | --- | --- | --- |
| U5.1 | `test_citation_validation.py` | unit extract/validate | PASS |
| U5.2 | `test_api_diagnostics.py` | 503 / 404 / citation / ranked_checks | PASS |
| U5.3 | `test_diagnostic_retrieval.py` | context + U3 ranking (25 tests in current suite slice) | PASS |
| U5.4 | Combined Umar diagnose slice | `python -m pytest -q tests/test_diagnostic_retrieval.py tests/test_citation_validation.py tests/test_api_diagnostics.py` → **35 passed** (2026-10-16) | PASS |
| U5.5 | Test app registers diagnostics router | `tests/conftest.py` matches `main.py` | PASS |
| U5.6 | UI contract handoff | `12_u4_u5_…` field freeze | PASS |

## Staging / CD unblock (closes Usman A3.5–A3.7 gaps)

| ID | Item | Evidence | Status |
| --- | --- | --- | --- |
| CD-1 | Workflow | `.github/workflows/deploy-staging.yml` | PASS |
| CD-2 | Branch triggers | `umar/mid1-graph-diagnostics`, `usman`, `main` | PASS |
| CD-3 | Ops | `GET /api/ops/version` public; `/api/ops/logs` token | PASS |
| CD-4 | Dedicated deploy key | GitHub `VM_SSH_KEY` = `halite_github_deploy` (not personal SSH) | PASS |
| CD-5 | Maintenance routes on VM | assets/history/diagnose reachable (unlike Usman audit stale VM) | PASS |
| CD-6 | Frontend default to staging | `frontend/.env.development` — see [`09`](09_frontend_shared_api.md) | PASS |

Durable ops guide: [`knowledge/context/modules/remote_backend.md`](../../knowledge/context/modules/remote_backend.md).

## Problems remaining (not Umar-owned to fix alone)

| Problem | Owner | Doc | Proposed fix |
| --- | --- | --- | --- |
| `GET /maintenance/assets` ~30s+ (N+1 count queries) | Usman | [`10`](10_perf_assets_api_handoff.md) | One Cypher `count(sr)` aggregation |
| ServiceRecords page fans out all histories | Shahmeer | [`10`](10_perf_assets_api_handoff.md) | Paginated list or selected-asset history only |
| Frontend CI `getRecord` mock missing | Shahmeer | [`06`](06_frontend_review_queue_handoff.md) | Add mock; do not skip test |
| Vite → localhost if env wrong | Team | [`09`](09_frontend_shared_api.md) | Use committed `.env.development`; restart Vite |
| A1 “isolated Neo4j” evidence still marked blocked in Usman docs | Usman | [`05`](05_usman_final_audit.md) | Reconcile: staging Aura now holds 2079; update Usman evidence SHA |
| Independent reviewer | Coordinator | — | Sign off against tip SHA |

**Redis:** not required for Mid-I; see [`10`](10_perf_assets_api_handoff.md).

## Commands agents should re-run (no secrets)

```powershell
# Staging honesty
Invoke-RestMethod https://dev1.corp.curatech.pk/halite-api/api/health
Invoke-RestMethod https://dev1.corp.curatech.pk/halite-api/api/ops/version

# History (813SK UUID)
Invoke-RestMethod https://dev1.corp.curatech.pk/halite-api/api/maintenance/assets/aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb/history

# Local Umar diagnose tests
cd backend
$env:DEMO_MODE='true'; $env:NEO4J_URI=''; $env:NEO4J_PASSWORD=''; $env:GROQ_API_KEY=''
python -m pytest -q tests/test_diagnostic_retrieval.py tests/test_citation_validation.py tests/test_api_diagnostics.py
```

Diagnose body (live Groq; do not log full explanation in public tickets):

```json
{
  "asset_id": "aa4e5d11-1895-48ec-84e5-d2f7c88aaaeb",
  "symptom_text": "pump leak hydraulic"
}
```

## Partner actions (agents)

### Shahmeer

1. [`06_frontend_review_queue_handoff.md`](06_frontend_review_queue_handoff.md) — fix `getRecord` mock.  
2. [`09_frontend_shared_api.md`](09_frontend_shared_api.md) — confirm staging `VITE_API_URL`.  
3. [`10_perf_assets_api_handoff.md`](10_perf_assets_api_handoff.md) — stop history fan-out; wait for Usman assets aggregation.  
4. [`12_u4_u5_diagnostics_handoff.md`](12_u4_u5_diagnostics_handoff.md) — wire Diagnostics UI; handle 503/404/loading honestly; use `part_name` (not `component`).

### Usman

1. Reconcile A1: staging now has real corpus + maintenance routes (Usman audit A3.6 FAIL is stale).  
2. Implement assets Cypher count (owned `maintenance.py`).  
3. Keep CD secrets/environment healthy; do not change diagnose ranking/citation without Umar DEC.

## Honesty constraints (do not regress)

- Never claim calibrated fault probabilities.  
- Never claim conflict F1 as diagnostic accuracy.  
- Never invent record IDs in UI or docs.  
- Always check `/api/health` (`graph_mode`, `llm_mode`, `maintenance_corpus_loaded`, `git_sha`) before claiming live Neo4j/LLM.  
- OPS_TOKEN / SSH keys never in git.

## Recommendation

- **Umar Mid-I scope:** treat U1–U5 as **closed** at SHA `a70652e` pending reviewer spot-check.  
- **Team Mid-I:** keep **do not merge** until Shahmeer CI + assets perf + Usman evidence update + reviewer approval.
