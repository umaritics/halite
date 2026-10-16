# Demo Ready Checklist (local)

Updated after setup on this machine.

## Running now

| Piece | Status | URL / note |
|---|---|---|
| Neo4j | Up (healthy) | http://localhost:7474 · bolt://localhost:7687 · user `neo4j` / password `localdevpassword` |
| Backend | Up | http://127.0.0.1:8000 · `/api/health` |
| Frontend | Up | http://localhost:5173 |
| Corpus | Ingested | **2,080** records · **118** airframes (includes one demo submit) |
| Review queue | Ready | **2** items waiting |
| Modes | Demo-ready | `graph_mode=neo4j` · `llm_mode=live` · `DEMO_MODE=false` |

## Open the app

1. Browser → http://localhost:5173
2. Switch domain to **Maintenance / Field Service**
3. Demo assets with long histories:
   - **813SK** (~153–154 records)
   - **508AE** (~118)
   - **860NW** (~113)

## Demo path (keep this short)

1. **Assets** → open `813SK` → show timeline  
2. **Submit / process a record** on that asset → say the pruning line out loud: *“examined 25 of N records”*  
3. **Review queue** → open a `needs_review` case → Accept (writes SUPERSEDES)  
4. **Diagnostics** → symptom on `813SK` → ranked checks with real FAA IDs  

## If something dies before the panel

```powershell
# Neo4j
cd U:\Development\NexiumApps\Halite
docker compose up -d neo4j

# Backend (new terminal)
cd U:\Development\NexiumApps\Halite\backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd U:\Development\NexiumApps\Halite\frontend
npm run dev
```

Health check:
```powershell
curl http://127.0.0.1:8000/api/health
python U:\Development\NexiumApps\Halite\halite_check.py
```

You want: `graph_mode: neo4j`, `llm_mode: live`, `maintenance_record_count ≈ 2079`.

## Notes

- Fresh ingest only loads records. Conflict scores for the three big demo assets are being backfilled (uses the existing LLM cache where possible).
- Review queue already has at least one live demo case from the diagnostic submit.
- Do **not** rely on in-memory / `DEMO_MODE=true` for maintenance — citation checks need Neo4j.
- If Groq returns 429: cached pairs still answer; keep the screen recording backup ready.
