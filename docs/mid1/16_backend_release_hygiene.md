# Umar + Usman Mid-I backend release hygiene

Date: 2026-10-16

Baseline `origin/main`: `b85dde00b8b942b174b506373fddf487606beffb`

Reviewed implementation SHA: `10136387417499e146f6a4014f24905c352308e0`

Branch: `fix/mid1-backend-release-hygiene`

The implementation SHA is the immutable backend/workflow revision reviewed by
this report. The PR head also contains this evidence document. No staging
deployment, restart, corpus mutation, frontend change, or merge to `main` was
performed.

## Verdicts

| Task | Verdict | Result |
| --- | --- | --- |
| 1. Protect staging | **PASS** | Obsolete branch push triggers removed; only CI-successful `main` SHAs are eligible; full SHA, ancestry, confirmation, exact-CI and protected-environment gates apply. |
| 2. Reconcile record count | **PASS (code fixed; live repair deferred)** | Exactly one orphan node identified; retry ingestion now repairs the missing `ABOUT` link idempotently. Production data was not modified. |
| 3. Health efficiency | **PASS** | Health contract preserved; Neo4j uses `count(sr)` and memory mode counts nodes without record materialization. Legacy software-project API description removed. |
| 4. Integration regression | **PASS locally / PARTIAL real graph** | `127 passed, 20 skipped`; local Docker/Neo4j unavailable due the existing Docker Desktop WSL failure. Prior hosted real-graph evidence remains green. |
| 5. Exact evidence | **PASS** | This document records policy, counts, changed files, tests, limitations, and U1–U5/A1–A4 continuity. |

## Deployment workflow policy

`.github/workflows/deploy-staging.yml` now:

1. reacts to successful completion of the full `CI` workflow for `main`, not
   pushes to `usman` or `umar/mid1-graph-diagnostics`;
2. refuses an automatic deployment when its successful workflow SHA is no
   longer the current `origin/main` tip;
3. accepts manual deploy/rollback only as a full 40-character SHA reachable
   from `main`, with `DEPLOY` or `ROLLBACK` confirmation;
4. queries Actions for a successful full CI run on the exact SHA before SSH;
5. passes only the validated, resolved SHA through the SSH action environment;
6. keeps the existing VM secrets and configuration unchanged;
7. uses the `staging` GitHub Environment, which administrators must configure
   with required reviewers and administrator bypass disabled;
8. records the current `/api/ops/version` SHA before deployment and verifies
   the exact approved SHA, Neo4j health, and assets endpoint afterward.

The known Shahmeer frontend failure leaves full CI red, so this policy blocks
release until Shahmeer's fix is integrated. The gate was not weakened. Editing
the workflow on this branch did not deploy or restart staging.

### Approved rollback

Use the previous SHA printed by the prior deployment's **Record currently
deployed revision for rollback** step, or capture `/api/ops/version` before a
release. Manually dispatch that full SHA with `rollback` and `ROLLBACK`. The SHA
must remain in `main` history, have successful full CI, receive the protected
environment approval, and pass the same post-deploy checks.

## Corpus count reconciliation

Read-only evidence on staging SHA
`b14c8eca972b69ff42c8fb76a6210a616191f8da`:

| Check | Result |
| --- | ---: |
| `/api/health` ServiceRecord nodes | 2,079 |
| `/api/maintenance/assets` assets | 118 |
| Sum of asset `record_count` | 2,078 |
| Records returned across all 118 histories | 2,078 |
| Unique history record IDs | 2,078 |
| Local source rows / unique IDs / nonblank asset keys | 2,079 / 2,079 / 2,079 |

The one legitimate source record omitted from asset history is
`AALA202506230216`, asset key `991AU`, difficulty date `2025-06-22`. It exists
as a `ServiceRecord` node but lacks an `ABOUT` relationship. The equality of
2,078 history rows and 2,078 unique history IDs shows no duplicate visible
relationship affecting the count. Software-domain nodes do not affect the
health count because it matches only the `ServiceRecord` label.

Root cause: ingestion previously checked for an existing record before the
link step. If a run stopped after node creation but before relationship
creation, every retry counted the row as a duplicate and skipped link repair.
The duplicate path now re-applies the idempotent link operation. Neo4j already
uses `MERGE`; memory mode now suppresses a duplicate identical edge. Regression
tests reproduce an interrupted ingest, repair it, and prove a second retry does
not duplicate the relationship.

No live data was changed. An authorized repair must first back up the graph,
record pre-repair counts, rerun the reviewed ingest procedure for the corpus,
then require 2,079 nodes, 2,079 `ABOUT` links, 118 assets, and presence of the
identified record in `991AU` history.

## Health optimization

`GraphRepository.count_service_records()` provides a shared contract:

- Neo4j: `MATCH (sr:ServiceRecord) RETURN count(sr) AS record_count`;
- memory: one node-count pass with no record dictionary list.

`backend/main.py` uses that method while retaining
`maintenance_record_count`, `maintenance_corpus_loaded`, and every other health
field. A regression test fails if health calls `list_service_records()`, and a
repository test proves the Neo4j query returns only the aggregate.

## Verification executed

| Verification | Result |
| --- | --- |
| `cd backend; python -m pytest -p no:cacheprovider -q` | **127 passed, 20 skipped in 6.59s** |
| Workflow YAML safe parse | **PASS**, one `deploy` job |
| `git diff --check` | **PASS** |
| Public staging health | **PASS**, Neo4j, 2,079 records, SHA `b14c8ec…` |
| Public assets/history reconciliation | **PASS**, 118 assets and 2,078 unique linked records |
| Local Docker real-graph run | **BLOCKED**, Docker Desktop WSL bootstrap error `0xc00000fd` |

The 20 skips are explicit Neo4j parameterizations when
`NEO4J_URI`/`NEO4J_PASSWORD` are absent. The fixture no longer invents
localhost defaults that can hang against a stale Docker port forward. Existing
integration evidence in `14_usman_umar_integration.md` records successful
backend and Docker real-graph jobs for the integrated baseline.

## Existing scope remains intact

Umar U1–U5:

- U1 diagnostic method and honesty unchanged;
- U2 bounded recent history, bounded fleet scan, and batched outcomes unchanged;
- U3 deterministic weights and stable tie-break unchanged;
- U4 live-model 503 boundary and citation allow-list unchanged;
- U5 diagnostic API contracts and regression tests remain green.

Usman A1–A4:

- A1 FAA ingest becomes safer on retry; corpus is not silently altered;
- A2 conflict processing/review behavior and 422/503 tests remain green;
- A3 Compose/VM secrets and configuration are preserved; release control is
  stricter and no deployment occurred;
- A4 router wiring and health fields are unchanged, with a cheaper count path.

Asset listing still uses one bounded aggregation, diagnostic retrieval remains
bounded and deterministic, citation validation remains active, controlled
404/422/503 behavior passes, conflict review is unaffected, and no API response
field was renamed.

## Files changed in implementation SHA

- `.github/workflows/deploy-staging.yml`
- `backend/agents/maintenance_agent.py`
- `backend/graph/memory_store.py`
- `backend/graph/queries.py`
- `backend/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_api_maintenance.py`
- `backend/tests/test_graph_maintenance.py`
- `backend/tests/test_maintenance_agent.py`
- `knowledge/context/04_data_and_graph.md`
- `knowledge/context/modules/maintenance_api.md`
- `knowledge/context/modules/remote_backend.md`
- `knowledge/decisions/DEC-20261016-main-only-staging-release.md`
- `knowledge/decisions/INDEX.md`
- `knowledge/flows/FLOW-deploy.md`

This evidence document is the only additional file in the documentation
commit. No Shahmeer-owned frontend file, test, API client, or dependency was
changed.

## Remaining final-release limitations

- Configure and verify required reviewers plus administrator-bypass prevention
  on the GitHub `staging` Environment; workflow YAML cannot create that setting.
- Shahmeer must fix the existing frontend test so full CI can become green.
- Repair the one live orphan only after authorization, backup, and recorded
  pre/post counts.
- Re-run real-Neo4j integration in hosted CI or after Docker Desktop is repaired.
- Merge and deploy only through separate explicit approval; this branch must
  remain an unmerged review PR until then.
