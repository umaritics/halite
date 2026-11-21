---
id: mod-devops
title: DevOps, runtime, CI
status: active
owners: [Usman]
updated: 2026-10-16
---

# Module: DevOps / runtime

## Compose / local

- `docker-compose.yml` — Neo4j + backend + frontend (dev). Not production.
- Setup guide: `docs/mid1_setup.md`.
- Runtime smoke: `backend/scripts/verify_mid1_runtime.py` (synthetic fixture in CI).

## CI (`.github/workflows/ci.yml`)

Backend installs `requirements-dev.txt`, runs Ruff with runtime-error rules
(`E9`, `F63`, `F7`, `F82`), then pytest with terminal and XML coverage plus JUnit.
Coverage/JUnit artifacts upload even after a failure. API/agent/service/graph/DB/
investigation coverage is reported; no unsupported whole-project 80% claim is made.

Ephemeral Neo4j 5 and PostgreSQL 16 services run both repository and session
contract tests. PostgreSQL session fixtures use a random schema and remove only
that schema. `SESSION_TEST_DATABASE_URL` must refer to a disposable test server.
Frontend tests/build and the Compose real-graph smoke remain independent jobs.
Pull requests run CI; push triggers include main/develop/usman and Umar's old
implementation branch. Staging deployment is a separate main-only gated workflow.

## Health semantics

| Field | Meaning |
| --- | --- |
| `graph_mode=neo4j` | Using Neo4j client path |
| `llm_mode=live` | Configured provider path (Groq or compatible adapter) |
| `maintenance_corpus_loaded` | ≥1 ServiceRecord visible to health |

## Evidence and operations

Historical Mid-I failures are documented in `docs/mid1/`; they are not current
runtime evidence. Current local evidence is in `docs/work/usman/WORK_LOG.md`.
Use `/api/health` before claiming graph/model/corpus state. Shared staging,
its backup and deployments belong to Umar under the vertical plan. This work
uses only disposable local databases and draft review branches.

## Hosted research browser proof

CI's disposable Docker smoke job additionally builds the frontend on the runner,
serves its production output through Vite preview (same-origin proxy to the
ephemeral Compose API), and runs `frontend/e2e/verify-research-ui.cjs` in Chromium.
The runner installs the pinned browser tool into its temporary directory; it
does not add it to the API image or deploy it. Screenshots, JSON proof and preview
log are uploaded as `research-browser-proof`. Test accounts/databases remain
ephemeral. Local heavy builds are avoided after the machine storage incident.

The host browser build uses a git-archived frontend copy under RUNNER_TEMP,
avoiding Compose-created root-owned bind-mount directories in the checkout.

## Dependency cleanup evidence

The backend install step writes a pip install report and installed-distribution
list. `docs/work/usman/verify_dependency_cleanup.py` audits actual backend imports
and checks the resolved environment against the retained baseline. Reports and
the summary ship with the backend test/coverage artifact. Unused LangChain roots
and python-docx must be absent; pandas/NumPy stay on the verified CSV versions.
Dotenv remains transitively installed, with a real `.env` Settings test. No
package installation is needed on the developer laptop for this verification.

Retained verification scripts import requests directly. The first hosted run
exposed its previous accidental LangChain transitive dependency during pytest
collection. Declare its baseline version explicitly and audit its presence.

After software retirement, pypdf and docx2txt are also removed because their
sole importer was deleted. Dependency audit now rejects both roots/packages.
