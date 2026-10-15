# Halite — Maintenance Diagnostic Support

Halite is a maintenance-focused diagnostic support prototype. It loads FAA Service Difficulty Reports into a knowledge graph, exposes asset histories and conflict-review workflows, and returns evidence-linked diagnostic investigations.

> Legacy software-domain modules remain in the repository, but they are outside the FYP-I Mid product scope.

## Mid-I workflow

- Browse real maintenance assets and dated service-record history.
- Submit a symptom for graph-grounded diagnostic investigation.
- Open source record identifiers used as evidence.
- Inspect conservative conflict classifications and the human review queue.
- Verify graph, corpus, and model mode through `/api/health`.

## Quick Start (Docker)

Full local stack: Neo4j, FastAPI, and the Vite frontend. See [`docs/mid1_setup.md`](docs/mid1_setup.md) for environment variables, ingestion, verification, and failure modes.

```bash
cp backend/.env.example backend/.env   # set GROQ_API_KEY if you need the LLM
docker compose up --build
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- API: [http://localhost:8000/health](http://localhost:8000/health)
- Neo4j Browser: [http://localhost:7474](http://localhost:7474) (`neo4j` / `localdevpassword`)

The backend container always uses `bolt://neo4j:7687`. If you run the API on the host instead, keep `NEO4J_URI=bolt://localhost:7687` and `DEMO_MODE=false` in `backend/.env`.

### Quick Start (Demo Mode, no Docker)

Demo mode runs with an in-memory graph and fallback model behavior. It is useful for unit tests and UI development, but it is not evidence of the required real-corpus demonstration.

### Backend on the host (Neo4j still in Docker)

```bash
docker compose up -d neo4j

cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env # Ensure NEO4J_URI=bolt://localhost:7687 and DEMO_MODE=false
uvicorn main:app --reload --port 8000
```

### Ingesting Maintenance Data

To populate the Neo4j database with FAA SDR maintenance records, you must first fetch the raw dataset:

```bash
cd backend
python scripts/fetch_sdr_data.py
```

This will download the SDR database into `backend/data/raw/` and extract `sdr_poc_corpus.csv` into `backend/data/processed/`.

Once downloaded, you can ingest the records into the running Neo4j instance by navigating to the **Ingest** tab in the web UI and selecting "Run ingest pipeline" under the Maintenance Domain, or via the API:

```bash
curl -X POST http://localhost:8000/api/maintenance/ingest
```

Finally, to evaluate the conflict engine against the ground-truth labels and regenerate the evaluation report:
```bash
cd backend
python scripts/evaluate_conflict_detection.py --sweep
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Production Setup

1. Create a free [Neo4j AuraDB](https://aura.neo4j.io) instance
2. Get a [Groq API key](https://console.groq.com)
3. Configure `backend/.env`:

```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_PASSWORD=your-password
GROQ_API_KEY=your-key
DEMO_MODE=false
```

4. Optionally configure Gitea for repo sync and webhooks

## Demo Flow (Supervisor Presentation)

1. Verify `/api/health` reports Neo4j mode and a loaded maintenance corpus.
2. Select a real asset and inspect its chronological service history.
3. Submit a symptom and show ranked checks with source record IDs.
4. Open a cited record from the evidence/history interface.
5. Show a real conflict-review item and explain its classification.
6. Demonstrate an unknown/no-data or model-unavailable case without invented output.
7. Show the reviewed branch/PR and hosted GitHub Actions run.

## Project Structure

```
Halite/
├── backend/          # FastAPI + agents + graph layer
├── frontend/         # React + Vite + Tailwind + 3D graph
├── docs/             # FYP specification
└── docker-compose.yml
```

## Team

Muhammad Umar (23I-0782), Muhammad Usman Al Haq (23I-0585), Shahmeer Atif (23I-0711)  
FAST NUCES, Islamabad
