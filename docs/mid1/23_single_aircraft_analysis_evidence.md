# Single-aircraft conflict analysis — 800NN

Owner: Shahmeer Atif (run and write-up) · Date: 2026-10-18 · Scope: one aircraft, one local scratch graph

This is a **bounded demonstration run**, not a full-corpus result and not a staging result.
Shared staging was not touched (it still reports 2,079 unscored records).

## What was run

| Item | Value |
| --- | --- |
| Aircraft | `800NN` — 13 service records, 3 FAA-authored ground-truth pairs |
| Why this aircraft | 13 records and 3 ground-truth pairs (890NN has 3 pairs in 9 records and would be cheaper); staging already shows a stored correction on 800NN, so the demo lines up |
| Graph | Throwaway Neo4j 5.20 container on port 7688, loaded with only the 13 `800NN` rows. The developer graph and staging were not used |
| Ingest | Through the new Ingest-page upload route (`POST /api/maintenance/ingest/upload`): 1 aircraft, 13 records, 0 skipped |
| Backend | Local FastAPI, `/api/health`: `graph_mode=neo4j`, `llm_mode=live`, model `openai/gpt-oss-120b` |
| Mode / threshold | `MAINT_ANALYSIS_MODE=legacy` (the default), `MAINT_CONFIDENCE_THRESHOLD=0.50` |
| Classification cache | Fresh and empty (`MAINT_DATA_DIR` pointed at a scratch folder), so every model result is a real call |

Commands (scratch password omitted; filter the corpus first):

```text
# 13-row CSV for one tail
python - <<'PY'   # filter backend/data/processed/sdr_poc_corpus.csv where RegistryNNumber == '800NN'

docker run -d --name halite-neo4j-scratch -p 7688:7687 -p 7475:7474 \
  -e NEO4J_AUTH=neo4j/<scratch-password> neo4j:5.20

# backend on the scratch graph
cd backend
NEO4J_URI=bolt://localhost:7688 NEO4J_PASSWORD=<scratch-password> DEMO_MODE=false \
  MAINT_DATA_DIR=<scratch-dir> MAINT_BUDGET_STATE_FILE=<scratch-dir>/budget.json \
  venv/bin/python -m uvicorn main:app --port 8000

# ingest, then analyse that aircraft only
curl -X POST localhost:8000/api/maintenance/ingest/upload -F "file=@800NN.csv;type=text/csv"
NEO4J_URI=... MAINT_DATA_DIR=<scratch-dir> MAINT_BUDGET_STATE_FILE=<scratch-dir>/budget.json \
  venv/bin/python scripts/backfill_conflict_scores.py --asset 800NN
```

## Result (script output)

| Measure | Value |
| --- | ---: |
| Records processed | 13 |
| Parse failures | 0 |
| Model classifications | 11 |
| Records screened without a model call | 2 |
| Successful provider requests | 55 |
| Tokens used | 29,386 |
| Rate-limit (HTTP 429) responses | 27, each retried successfully |
| `SUPERSEDES` edges created | 4 |
| Status | 7 `no_action`, 4 `auto_accepted`, 2 `needs_review` |
| Confidence (score) min / median / max | 0.00 / 0.55 / 0.90 |

Per-record states are in [logs/single_aircraft_800NN_results.json](logs/single_aircraft_800NN_results.json).

## Against the FAA ground truth

| Check | Result |
| --- | --- |
| Ground-truth pairs for 800NN found as `SUPERSEDES` | **3 of 3** |
| `SUPERSEDES` edges not in the ground-truth file | 1 (`AALA202503100492` DOOR TRACK ← `AALA202506090459` DOOR, three months apart) |

The ground-truth file lists only corrections the FAA itself recorded, so an edge that is
absent from it is **unverified, not shown to be wrong**. No precision figure is claimed
from one aircraft. Two further records were sent to human review (a `contradicts` and a
`partial_supersedes`).

## What the UI shows for this aircraft

- Service Records: score and label per record, labelled "heuristic, not a probability";
  records with no candidates read "No conflict found (N comparisons)".
- Asset History: the older DOOR TRACK record is greyed and reads "Corrected by …
  component changed DOOR TRACK → DOOR"; text comes from the stored records only.
- Review Queue (2): incoming record beside the retrieved prior record, the model's
  rationale, Accept / Reject.
- Knowledge Graph for 800NN: 14 nodes, 29 edges (13 `ABOUT`, 12 `PRECEDED_BY`, 4 `SUPERSEDES`). The
  four `SUPERSEDES` edges are thick and amber and the superseded record is grey. This needs the
  layout-spacing fix (branch `fix/mid1/graph-spacing`); before it, small graphs hid their edges.

## Limits — do not over-claim

- One aircraft, 13 records. It shows the method works end to end; it is not a measure
  of accuracy, and nothing here scales to the 2,079-record corpus.
- `legacy` mode only. The cost cascade was not run.
- Token and request figures are for this aircraft only (about 2,260 tokens and 4.2
  requests per record). They must not be extrapolated to the full corpus.
- Model `openai/gpt-oss-120b` from the developer's local environment. Staging runs
  `openai/gpt-oss-20b`, so staging results would differ.
- Local scratch graph, not staging. Staging was not written to.
