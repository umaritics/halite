# Halite — Living Knowledge Graph Prototype

Institutional memory for software teams. Halite captures, stores, and serves the reasoning layer behind your codebase — decisions, components, and their relationships in a queryable knowledge graph.

> Originally specified as **LogicVault** — this prototype is branded **Halite**.

## Features

- **Knowledge Graph** — Components, decisions, commits, tickets, and documents with relationship edges
- **AI Chat** — Groq-powered Q&A grounded in graph context (demo mode without API key)
- **Document Ingestion** — Extract decisions from PDF, DOCX, TXT, MD uploads
- **Gitea Integration** — Sync commits/issues, analyze code, webhook invalidation
- **Invalidation Alerts** — Flag decisions when linked files change
- **3D Graph Visualization** — `react-force-graph-3d` + Three.js crystal nodes
- **Halite Theme** — Dark crystal aesthetic with light/dark toggle in Settings

## Quick Start (Demo Mode)

Demo mode runs with an in-memory graph and mock LLM responses — no Neo4j or Groq required.

### Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
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

1. Open Halite — see seeded demo decisions (JWT, PostgreSQL)
2. **Chat** — ask "Why did we choose JWT?"
3. **Graph** — explore 3D knowledge graph, click nodes
4. **Decisions** — add a manual decision
5. **Ingest** — upload a meeting transcript or sync Gitea
6. **Ingest → Sync Commits** — triggers invalidation on auth module
7. **Alerts** — JWT decision flagged as needs review
8. **Chat again** — see warning badges on outdated sources

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
