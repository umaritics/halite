# Usman handoff — corpus is unscored (all confidence=1 / auto_accepted)

**Owner to execute:** Muhammad Usman Al Haq (conflict engine, ingest, maintenance APIs, staging Neo4j ops)  
**Diagnosed by:** Umar (2026-10-16)  
**Priority:** High for Mid-I demo of Review Queue / conflict story  
**Branch to land follow-up on:** `main` (or Usman working branch merged to `main`)  
**Do not treat as Umar/diagnostics work** — do not edit `diagnostics.py` / ranking to “fix” this.

Knowledge agents must also open:

| Topic | Path |
| --- | --- |
| Conflict module | [`knowledge/context/modules/conflict_engine.md`](../../knowledge/context/modules/conflict_engine.md) |
| Ingest flow | [`knowledge/flows/FLOW-ingest.md`](../../knowledge/flows/FLOW-ingest.md) |
| Conflict/review flow | [`knowledge/flows/FLOW-conflict-review.md`](../../knowledge/flows/FLOW-conflict-review.md) |
| Maintenance APIs | [`knowledge/context/modules/maintenance_api.md`](../../knowledge/context/modules/maintenance_api.md) |
| Staging / CD | [`knowledge/context/modules/remote_backend.md`](../../knowledge/context/modules/remote_backend.md) |
| Ownership | [`knowledge/context/02_ownership_mid1.md`](../../knowledge/context/02_ownership_mid1.md) |
| Agent rules | [`AGENTS.md`](../../AGENTS.md) |

---

## 1. Symptom (what the team sees)

| Observation | Expected for Mid-I demo |
| --- | --- |
| Every ServiceRecord shows **confidence = 1.0** | Mix of scored confidences after conflict adjudication |
| Every record **status = auto_accepted** | Some `needs_review`, some `superseded`, some `auto_accepted` |
| Review Queue empty | Non-empty queue with real conflict candidates |
| No “correction / supersedes” story on known pairs | Ground-truth pair linked with `SUPERSEDES` |

Frontend ConfidenceBar / StatusChip are likely **correctly rendering stored fields**. The data itself was never conflict-scored.

---

## 2. Live proof (staging Neo4j / Aura — 2026-10-16)

Staging health at diagnosis time: `git_sha≈b14c8ec…`, `maintenance_record_count=2079`, `graph_mode=neo4j`.

### Aggregate (Cypher)

```cypher
MATCH (sr:ServiceRecord)
RETURN
  count(sr) AS total,
  count(CASE WHEN sr.status = 'auto_accepted' THEN 1 END) AS auto_accepted,
  count(CASE WHEN sr.status = 'needs_review' THEN 1 END) AS needs_review,
  count(CASE WHEN sr.status = 'superseded' THEN 1 END) AS superseded,
  min(sr.confidence) AS min_conf,
  max(sr.confidence) AS max_conf,
  avg(sr.confidence) AS avg_conf,
  count(CASE WHEN sr.confidence = 1.0 OR sr.confidence = 1 THEN 1 END) AS conf_exactly_1
```

| Metric | Observed |
| --- | --- |
| total | **2079** |
| auto_accepted | **2079** |
| needs_review | **0** |
| superseded | **0** |
| min/max/avg confidence | **1 / 1 / 1** |
| conf_exactly_1 | **2079** |

### Edges

```cypher
MATCH ()-[r:SUPERSEDES]->() RETURN count(r) AS supersedes_edges
MATCH ()-[r:PRECEDED_BY]->() RETURN count(r) AS preceded_by_edges
```

| Rel | Count | Meaning |
| --- | --- | --- |
| `SUPERSEDES` | **0** | Conflict engine never applied adjudication |
| `PRECEDED_BY` | **~1961** | Chronology from **ingest only** — not conflict scoring |

### Ground-truth demo pair (must work after backfill)

From Usman Mid-I evidence / corpus profile:

| Field | Value |
| --- | --- |
| Tail | `811NN` |
| Older / superseded candidate | `AALA202501025620` |
| Newer / correcting candidate | `AALA202501035620` |

Observed **before** backfill:

```cypher
MATCH (a:ServiceRecord {record_id: 'AALA202501025620'}),
      (b:ServiceRecord {record_id: 'AALA202501035620'})
RETURN a.status, a.confidence, b.status, b.confidence,
       exists((b)-[:SUPERSEDES]->(a)) AS b_supersedes_a
```

Result: both `auto_accepted`, confidence `1`, `b_supersedes_a = false`.

### API proof

```text
GET https://dev1.corp.curatech.pk/halite-api/api/maintenance/review-queue
→ []  (count 0)
```

---

## 3. Root cause (code — not a UI bug)

### 3.1 Bulk ingest writes placeholder “clean” defaults

File: `backend/agents/maintenance_agent.py` → `_ingest_records`

Every new `ServiceRecord` is created with:

```python
"status": "auto_accepted",
"confidence": 1.0,
```

Ingest **does not** call `process_record`. It only creates Asset/ServiceRecord, `ABOUT`, and `PRECEDED_BY`.

Documented intentionally in `backend/scripts/backfill_conflict_scores.py` header:

> Bulk ingestion writes records quickly but bypasses the LLM scoring engine…

### 3.2 Conflict scoring is a separate pipeline

| Entry | Role |
| --- | --- |
| `POST /api/maintenance/records` | Run `process_record` on one already-ingested (or inline) record |
| `GET /api/maintenance/records/{id}` | Dry-run classification (needs live Groq; **503** if not live) |
| `backend/scripts/backfill_conflict_scores.py` | Bulk chronological re-score |
| `services/conflict_engine.py` | `find_candidate_pairs` → classify → adjudicate → `score_confidence` → `route` → optional `SUPERSEDES` + status/confidence update |

Default threshold: `settings.MAINT_CONFIDENCE_THRESHOLD` (see `backend/.env.example` / `config.py`; conflict module also documents a provisional default).

### 3.3 Staging corpus never got the second step

Ingest (or restore) loaded 2079 rows → all left at ingest defaults → Review Queue empty → demo looks “everything is clean.”

---

## 4. What “good” looks like after fix (acceptance)

Agents must record SHA, commands, and counts. Do **not** claim PASS from code existence alone.

| ID | Check | Pass criteria |
| --- | --- | --- |
| C1 | Health | `graph_mode=neo4j`, corpus still ~2079 (or documented delta) |
| C2 | Confidence not all 1.0 | `conf_exactly_1 < total` after scoring run (or documented subset) |
| C3 | Review queue | `GET /api/maintenance/review-queue` length **≥ 1** for Mid-I demo |
| C4 | Ground-truth pair | After processing `AALA202501035620` (and/or backfill on `811NN`): statuses/confidence updated; preferably `(b)-[:SUPERSEDES]->(a)` **or** explicit `needs_review` with classification evidence — document which |
| C5 | SUPERSEDES or needs_review | At least one of: `SUPERSEDES` count ≥ 1 **or** `needs_review` ≥ 1 on staging |
| C6 | Live Groq | Backfill / `process_record` run with `groq.is_live=True` for Mid-I honesty |
| C7 | Evidence note | Update this file or `05`/`07` with post-run JSON counts + Actions/ops SHA |
| C8 | No secret leak | No `GROQ_API_KEY` / Neo4j password in git, screenshots, or CI logs |

---

## 5. Recommended execution plan (agents: follow in order)

### Phase A — Demo-critical (do this first, cheap)

Goal: non-empty Review Queue + one explainable conflict pair for Mid-I.

1. Confirm staging secrets on VM: `GROQ_API_KEY`, Neo4j URI/password, `DEMO_MODE=false`.
2. Confirm live model:
   ```bash
   curl -s https://dev1.corp.curatech.pk/halite-api/api/health
   # require llm_mode=live (or equivalent is_live path)
   ```
3. Process the known correcting record via API (mutates graph):
   ```bash
   curl -s -X POST https://dev1.corp.curatech.pk/halite-api/api/maintenance/records \
     -H "Content-Type: application/json" \
     -d "{\"record_id\":\"AALA202501035620\"}"
   ```
4. Optionally process a few more IDs from `backend/data/processed/ground_truth_pairs.csv` (gitignored on hosts that have it) — **newer** record_id of each pair.
5. Verify:
   ```bash
   curl -s https://dev1.corp.curatech.pk/halite-api/api/maintenance/review-queue | head
   curl -s https://dev1.corp.curatech.pk/halite-api/api/maintenance/records/AALA202501035620
   ```
6. Record sanitized response fields: `status_applied`, `confidence`, `classification.label`, `adjudication.action` — **no raw secrets**.

### Phase B — Asset-scoped backfill (recommended)

On a host that can reach the **same** Neo4j Aura DB as staging (VM container preferred):

```bash
cd /path/to/halite/backend   # or docker compose exec backend bash
# Ensure .env has NEO4J_* and GROQ_API_KEY; DEMO_MODE=false

python scripts/backfill_conflict_scores.py --asset 811NN
# then other demo tails if needed, e.g. 813SK (dense history — costlier)
```

Script flags (from source):

| Flag | Meaning |
| --- | --- |
| `--asset TAIL` | Repeatable; filter to asset tail_number |
| `--limit N` | Cap records processed |
| `--resume` | Skip records where `confidence != 1.0` |

### Phase C — Full corpus (optional / expensive)

```bash
python scripts/backfill_conflict_scores.py
# or with resume after interruption:
python scripts/backfill_conflict_scores.py --resume
```

Expect: many LLM calls, rate limits, hours possible. Prefer `--asset` batches + sleep already in script (`time.sleep(0.1)`).

Use `GROQ_API_KEY_FALLBACK` if configured (see `groq_service.py` 429 switch).

### Phase D — Redeploy / evidence

1. If script changes are required (see §6), commit on Usman/`main`, let **Deploy staging backend** run.
2. Append results to this doc or `docs/mid1/05_usman_final_audit.md` / `07_usman_release_readiness.md`.
3. Notify Shahmeer: Review Queue should now have items; ConfidenceBar should show non-1.0 values where scored.

---

## 6. Critical script caveat (`allow_stub=True`)

Current `backfill_conflict_scores.py` calls:

```python
process_record(..., allow_stub=True)
```

That **bypasses** the production guard that refuses canned LLM output when Groq is not live.

| Risk | Mitigation |
| --- | --- |
| Running backfill without live Groq produces **meaningless** confidence/status | Require `groq.is_live` before starting; **patch script to `allow_stub=False`** for staging runs (Usman-owned one-line fix + test) |
| Mid-I overclaim | Evidence must show `llm_mode=live` during the run |

**Agent action:** Prefer patching `allow_stub=False` for staging backfill before claiming Mid-I conflict evidence. Keep `allow_stub=True` only in unit tests.

---

## 7. Files Usman agents may edit

| Allowed | Forbidden without handoff DEC |
| --- | --- |
| `backend/scripts/backfill_conflict_scores.py` | `backend/api/routes/diagnostics.py` |
| `backend/services/conflict_engine.py` | `backend/services/diagnostic_retrieval.py` |
| `backend/agents/maintenance_agent.py` (if changing ingest defaults / post-ingest hook) | `backend/services/citation_validation.py` |
| `backend/api/routes/maintenance.py` | Frontend pages (Shahmeer) except coordinating Review Queue UX |
| `docs/mid1/05_*`, `07_*`, this file | Inventing SUPERSEDES edges without engine |

Optional product improvement (document if done): after ingest, leave `confidence=null` or `status=unscored` instead of faking `1.0` / `auto_accepted`, then backfill sets real values — **coordinate UI** with Shahmeer (`ConfidenceBar`, filters).

---

## 8. Sanity Cypher / API checklist (copy-paste)

```cypher
// After backfill — expect not all 1.0 / not all auto_accepted
MATCH (sr:ServiceRecord)
RETURN sr.status AS status, count(*) AS n
ORDER BY n DESC

MATCH ()-[r:SUPERSEDES]->() RETURN count(r) AS supersedes

MATCH (a:ServiceRecord {record_id:'AALA202501025620'}),
      (b:ServiceRecord {record_id:'AALA202501035620'})
OPTIONAL MATCH (b)-[s:SUPERSEDES]->(a)
RETURN a.status, a.confidence, b.status, b.confidence, s IS NOT NULL AS linked
```

```bash
curl -s https://dev1.corp.curatech.pk/halite-api/api/health | jq '{graph_mode,llm_mode,maintenance_record_count,git_sha}'
curl -s https://dev1.corp.curatech.pk/halite-api/api/maintenance/review-queue | jq 'length'
```

Local tests (do not replace staging proof):

```bash
cd backend
DEMO_MODE=true python -m pytest -q tests/test_conflict_engine.py tests/test_api_maintenance.py
```

---

## 9. Demo script impact

| Demo beat | Before this fix | After Phase A/B |
| --- | --- | --- |
| Assets / history | Works | Works |
| Diagnostics (Umar) | Works on history | Still works; may show superseded flags if edges exist |
| Review Queue (Usman/Shahmeer) | **Empty — not demoable** | Show needs_review + accept/reject |
| Conflict honesty | False “all clean” | Real scored subset |

---

## 10. Anti-ambiguity rules for agents

1. **Do not** “fix” by hardcoding random `needs_review` without running the engine.  
2. **Do not** claim conflict F1 / confidence as diagnostic accuracy (Umar diagnostics).  
3. **Do not** wipe Neo4j volume to re-ingest unless explicitly authorized — prefer in-place backfill.  
4. **Do not** commit `backend/.env`, FAA CSV, or keys.  
5. **Do** record before/after counts in Mid-I evidence.  
6. **Do** keep ingest idempotent; backfill should update existing nodes, not duplicate OCNs.  
7. If API returns **503** on `/records/{id}` or `/records`, Groq is not live — fix secrets/restart before scoring.

---

## 11. Ownership sign-off

| Role | Action |
| --- | --- |
| **Usman** | Execute Phase A → B; patch `allow_stub` if needed; update evidence; notify team |
| **Shahmeer** | After C3/C5 green, verify Review Queue + ConfidenceBar against staging |
| **Umar** | No ranking change required; diagnose may benefit from real superseded flags once edges exist |

**Status:** OPEN — diagnosed; not executed as of this document’s creation.  
**Next owner:** Usman agent / Usman human on staging Neo4j + live Groq.
