# Mid-I test and delivery evidence

Last updated: 2026-10-15<br>
Owner: Muhammad Usman Al Haq<br>
Branch: `usman`<br>
Baseline commit: `8840c68c32054bf1e9dd1505bbbdef4e22d26f6c`

This file records observed results. It is not a substitute for a hosted GitHub Actions run, reviewer approval, or real-runtime screenshots.

## Local results

| Gate | Command | Observed result |
| --- | --- | --- |
| Owned maintenance/conflict tests | `cd backend && python -m pytest -q tests/test_api_maintenance.py tests/test_conflict_engine.py tests/test_maintenance_agent.py` | PASS: 59 tests; 2 local pytest-cache permission warnings |
| Complete backend suite (CI-equivalent no-Neo4j environment) | `cd backend && python -m pytest -q` | PASS: 102 passed, 16 Neo4j cases skipped, 2 local pytest-cache permission warnings |
| Frontend tests | `cd frontend && npm test -- --run` | FAIL: 12 passed, 1 failed; `ReviewQueue.test.jsx` mock lacks `maintenanceAPI.getRecord` |
| Frontend production build | `cd frontend && npm run build` | PASS: 857 modules transformed; chunk-size warning only |
| Compose render | `docker compose config --quiet` | PASS; local Docker config emitted an access warning in the restricted runner |

The failing frontend test belongs to the frontend owner under the Mid-I work split. It is intentionally not hidden or bypassed; CI will remain red until the test fixture is corrected in the frontend branch.

## Docker and real-runtime evidence

To be filled only from observed output after the stack starts:

| Evidence | Value |
| --- | --- |
| `docker compose up --build -d` | BLOCKED on this host: Docker BuildKit exited while pulling/building after Windows reported that the paging file was too small |
| `docker compose up -d neo4j` | BLOCKED on this host: Docker Desktop's WSL engine failed to bootstrap (`0xc00000fd`) after the resource failure |
| Hosted Compose build/start | PASS in GitHub Actions job `116587631664` |
| Container status | Full stack started; backend health and frontend HTTP checks passed remotely |
| `graph_mode` | `neo4j` asserted by hosted smoke |
| `using_memory_graph` | `false` asserted by hosted smoke |
| `maintenance_corpus_loaded` | `true` after synthetic smoke-fixture ingestion |
| `maintenance_record_count` | At least 3 asserted; fixture created exactly 3 records on the fresh runner |
| `llm_mode` | Fallback/no-key behavior verified through transparent HTTP 503 |
| Real local corpus asset/record | `813SK` / `SWIA2025111676447` (153 records in local ignored FAA corpus) |
| Real local conflict pair | `AALA202501025620` superseded by `AALA202501035620`, tail `811NN` |
| Hosted synthetic review records | `CI-SMOKE-002` accepted and `CI-SMOKE-003` rejected; original text preservation asserted |

## Hosted delivery evidence

| Item | Value |
| --- | --- |
| DevOps branch commit | `2651eab580c2c3e46069dec1a5c1364f8fafb95b` on `origin/usman` |
| GitHub Actions run URL | <https://github.com/umaritics/halite/actions/runs/38782968975> |
| Backend hosted job | PASS: <https://github.com/umaritics/halite/actions/runs/38782968975/job/116587631265> |
| Docker hosted job | PASS: <https://github.com/umaritics/halite/actions/runs/38782968975/job/116587631664> |
| Frontend hosted job | FAIL: <https://github.com/umaritics/halite/actions/runs/38782968975/job/116587632014> — stale frontend test mock |
| Independent reviewer | Pending |
| Release tag | Pending; branch intentionally not merged or tagged yet |
| Deployment URL and health check | Pending or explicitly not deployed |

## Known limitations

- The frontend suite currently has one failing Review Queue test, so the new CI workflow is expected to fail at that gate until the frontend owner fixes its API mock.
- The Compose file renders successfully, but an end-to-end local container run is not yet proven on this machine because Docker Desktop exhausted the available Windows paging file during image build. Increase available virtual memory/restart Docker, then rerun the documented startup command.
- A successful HTTP health response alone is insufficient. Mid-I real-data evidence requires Neo4j mode and a non-zero ingested maintenance corpus.
- Live conflict/diagnosis behavior depends on a configured, available model or a clearly identified valid cache. Fallback output must not be described as live inference.
- Existing threshold evaluation used a small sample; no new accuracy or generalization claim is made here.
