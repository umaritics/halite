# Halite Mid-I setup and verification

This guide reproduces the maintenance-only vertical slice: Neo4j, FastAPI, the React/Vite UI, FAA SDR ingestion, health verification, and conflict-review APIs. Run commands from the repository root unless a step says otherwise.

## Requirements

- Docker Desktop with Docker Compose v2 (recommended path)
- Git
- For host-based development: Python 3.11+ and Node.js 20+
- At least 4 GB free RAM and enough disk space for container images and FAA data

Do not commit `backend/.env`, downloaded FAA CSV files, API keys, database passwords, or screenshots that expose them.

## Configuration

Copy `backend/.env.example` to `backend/.env`. Configure only the values needed for the selected mode:

| Variable | Purpose | Local Compose value |
| --- | --- | --- |
| `NEO4J_URI` | Neo4j Bolt endpoint | Overridden to `bolt://neo4j:7687` in Compose |
| `NEO4J_USERNAME` | Neo4j user | `neo4j` |
| `NEO4J_PASSWORD` | Database password | Set in the shell or use the documented local default |
| `DEMO_MODE` | Selects in-memory fallback when true | Overridden to `false` in Compose |
| `GROQ_API_KEY` | Enables live conflict/diagnosis model calls | Optional for health, required for live model behavior |
| `GROQ_MODEL` | Groq model identifier | See `.env.example` |
| `MAINT_DATA_DIR` | Base directory containing `processed/` | `data` inside the backend container |
| `MAINT_CONFIDENCE_THRESHOLD` | Conservative conflict routing threshold | Keep the reviewed value; do not tune for demo optics |

The local Compose password defaults to `localdevpassword`. To override it in PowerShell before startup:

```powershell
$env:NEO4J_PASSWORD = "choose-a-local-password"
```

Never reuse that development password for AuraDB or deployment.

## Full Docker startup

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Services:

- UI: <http://localhost:5173>
- API health: <http://localhost:8000/api/health>
- Neo4j Browser: <http://localhost:7474>

Wait until `neo4j` and `backend` report healthy. Verify the runtime:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/maintenance/assets
curl http://localhost:8000/api/maintenance/review-queue
```

For a real-data demonstration, health must report `graph_mode: "neo4j"`, `using_memory_graph: false`, `demo_mode: false`, and—after ingestion—`maintenance_corpus_loaded: true` with a non-zero runtime count. `llm_mode: "fallback"` means a live Groq-backed conflict or diagnosis request must fail transparently or use an explicitly identified valid cache; it must not be presented as live inference.

## FAA SDR data and idempotent ingestion

The fetch step downloads public FAA data and creates the processed POC corpus. It requires network access and can take time.

```bash
cd backend
python scripts/fetch_sdr_data.py
cd ..
curl -X POST http://localhost:8000/api/maintenance/ingest
```

Because `backend/` is bind-mounted at `/app`, `backend/data/processed/sdr_poc_corpus.csv` is visible to the API container. Ingestion uses stable record identifiers and skips existing records. A second ingestion should report zero newly created records and a non-zero `duplicates_skipped` count; verify that before using it as idempotency evidence.

Do not run `docker compose down -v` against the only demo corpus: `-v` deletes the local Neo4j volume.

## Host development with Docker Neo4j

Start only the graph:

```bash
docker compose up -d neo4j
```

In `backend/.env`, set `NEO4J_URI=bolt://localhost:7687` and `DEMO_MODE=false`, then:

```bash
cd backend
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# bash/zsh: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

## Test and release checks

```bash
cd backend
python -m pytest -q
cd ../frontend
npm test
npm run build
cd ..
docker compose config --quiet
```

GitHub Actions runs those backend, frontend, build, and Compose validation gates without real secrets. A local pass does not substitute for a hosted Actions run; record the passing run URL and reviewed PR before release.

The hosted Docker job additionally performs a real Neo4j integration smoke test with the non-sensitive fixture at `backend/tests/fixtures/mid1_smoke.csv`. To run the same assertions after the stack is healthy:

```bash
docker compose exec -T backend python scripts/verify_mid1_runtime.py
```

The success marker is `MID1_RUNTIME_SMOKE=PASS`. This fixture validates wiring and API behavior only; it is not evidence of FAA corpus accuracy.

## Isolated real-FAA corpus verification

This is a separate, manually authorized gate. Never upload the ignored FAA corpus to normal pull-request CI, and never delete the team's only demonstration database or volume.

1. Use an approved host with Docker/Neo4j and copy the ignored processed corpus through the team's approved private transfer channel.
2. Create a dedicated Neo4j database or dedicated Compose project/volume. The development Compose has a fixed container name and published ports, so use a reviewed override with unique names/ports and do not point at the only demonstration database.
3. Set a non-default test password through the environment, keep `DEMO_MODE=false`, and start the isolated stack.
4. Ingest once, capture returned counts, ingest again, and require zero new records on the second run.
5. Check health, asset/history, and the correction pair. Sanitize passwords, tokens, private paths, and full narratives from the retained log.

Representative commands after the isolated target and override have been approved:

```powershell
$env:COMPOSE_PROJECT_NAME = "halite_usman_real_audit"
$env:NEO4J_PASSWORD = Read-Host -MaskInput "Temporary audit Neo4j password"
docker compose -f docker-compose.yml -f docker-compose.real-audit.override.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.real-audit.override.yml ps
curl.exe -X POST http://127.0.0.1:8000/api/maintenance/ingest
curl.exe -X POST http://127.0.0.1:8000/api/maintenance/ingest
curl.exe http://127.0.0.1:8000/api/health
curl.exe http://127.0.0.1:8000/api/maintenance/assets/813SK/history
```

The override is intentionally not invented here because its ports, database name, host, and credential source require team approval. Acceptance requires runtime proof for 2,079 records/118 assets (or a documented updated corpus), `813SK`, `SWIA2025111676447`, both `811NN` correction records in submission chronology, source-ID preservation, and duplicate-safe re-ingestion. At the 2026-10-15 audit this gate is **BLOCKED** because Docker Desktop fails WSL startup with `0xc00000fd`, and the persistent VM does not expose the maintenance routes.

## Staging and production boundary

`docker-compose.yml` is development-only: it publishes Neo4j ports, permits `localdevpassword`, bind-mounts source, and runs reload/dev servers. Do not use it unchanged for staging or production. `docker-compose.vm.yml` describes a hardened backend container, but the public VM currently serves an older API: health returns 200 while `/api/maintenance/assets` returns 404. No automatic deployment workflow exists.

Before claiming CD, the team must approve the target host/Aura database, secret store and deployment credentials, frontend origin/DNS/TLS, branch or release trigger, immutable image/version identification, database backup/migration policy, and rollback command. A deployment must record its Git SHA and pass current health, asset, history, and controlled model checks.

## Live model verification boundary

`GROQ_API_KEY` enables the client; `GROQ_MODEL` selects the reviewed model; `GROQ_API_KEY_FALLBACK` is an optional rate-limit fallback supported by code but intentionally omitted from the public example. A no-key uncached diagnostic must return HTTP 503. `groq_configured=true` alone is not live-call proof. The owner must demonstrate one successful, citation-validated `/api/maintenance/diagnose` request on an approved ingested asset and retain only sanitized status/schema evidence. The service switches once to the fallback key for a 429/rate-limit condition; other provider errors are surfaced and there is no general exponential-backoff policy.

## Runtime dependency diagram

```mermaid
flowchart LR
    Browser[Browser on :5173] -->|/api proxy| API[FastAPI on :8000]
    API -->|Bolt| Neo4j[Neo4j on :7687]
    API -. live calls when configured .-> Groq[Groq API]
    Corpus[FAA SDR processed CSV] -->|idempotent ingest| API
    Actions[GitHub Actions] --> BackendTests[PyTest]
    Actions --> FrontendChecks[Vitest and Vite build]
```

## Troubleshooting

- If health reports `graph_mode: "memory"`, check `docker compose logs backend neo4j`, the Neo4j password, and service health. Do not claim real-graph operation.
- If the corpus count is zero, confirm the processed CSV exists and run the ingestion request once.
- If model-backed endpoints return 503, verify `GROQ_API_KEY` and rate limits; keep the failure visible.
- If Windows blocks `npm.ps1`, invoke `npm.cmd` or use Command Prompt.
- If ports 5173, 7474, 7687, or 8000 are occupied, stop the conflicting local service or intentionally update and document the port mapping.
