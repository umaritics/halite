# Halite — Proposal Defense Package

Everything needed to test, present and defend the maintenance POC.

---

# PART 1 — Verified numbers

Use only these. If a number is not here, do not say it.

| Claim | Value | N | Source |
|---|---|---|---|
| Misdiagnosis rate — corrections naming a different part | **65.2%** | 141 pairs | `docs/misdiagnosis_density.md` |
| — different JASC code | 42.6% | 141 | same |
| — different part location | 47.5% | 141 | same |
| **Pair-level detection precision** | **0.804** | 141 | `evaluation_results.md` §3 |
| **Pair-level detection recall** | **0.610** | 141 | same |
| Candidate-level precision | 0.903 | 350 | §5 |
| Candidate-level recall | 0.660 | 350 | §5 |
| **Engine F1** | **0.762** | 350 | §5 |
| **Engine false-conflict rate** | **0.048** | 209 neg | §5 |
| Baseline F1 | 0.536 | 350 | §5 |
| **Baseline false-conflict rate** | **1.000** | 209 neg | §5 |
| Records with no candidate prior after pruning | 77.8% (1,617 / 2,079) | — | §2 |
| All-pairs cost on largest asset | 11,628 → ≤25 per record | 153 records | §2 |
| Corpus | 2,079 records, ~60 airframes | — | ingest |
| Conflicts detected | 121 | — | §1 |

**Three sentences you should be able to say without notes:**

1. Two thirds of corrections in FAA maintenance data blame a different component than the original report — we measured it, on 141 author-recorded pairs.
2. The engine finds 61% of known supersessions and is right 80% of the time when it acts.
3. The recency baseline never abstains — false-conflict rate 1.000 against our 0.048.

---

# PART 2 — UI acceptance test (do this yourself, ~20 minutes)

Backend on Neo4j, corpus loaded, frontend running. Tick each.

### Pre-flight
- [ ] `/api/health` → `graph_mode: neo4j`, `llm_mode: live`, `using_memory_graph: false`
- [ ] `maintenance_record_count` ≈ 2,079
- [ ] Settings page status card shows the same values as raw `/api/health`

### Software domain (must not have regressed)
- [ ] Chat responds and cites a decision
- [ ] Decisions page lists seeded decisions
- [ ] Knowledge Graph renders; node cap label visible
- [ ] Alerts page loads

### Domain switch
- [ ] Switcher toggles nav between the two domains
- [ ] Selection survives a page reload
- [ ] Footer text changes with the domain

### Assets
- [ ] Grid lists airframes with record counts
- [ ] `813SK` shows 153
- [ ] Search by tail number filters
- [ ] Clicking an asset opens its history

### Asset history
- [ ] Timeline is chronological
- [ ] Superseded records visibly diminished, with rationale
- [ ] Status chips render correctly

### Service Records
- [ ] Status filters work (All / Auto Accepted / Needs Review / Accepted / Rejected / Superseded)
- [ ] Confidence values **vary** — not all 1.00, not all 0.50
- [ ] `unscored` renders distinctly from `auto_accepted`
- [ ] Search across discrepancy text works

### Review Queue — the critical screen
- [ ] Queue is **not empty** — note the exact count: ______
- [ ] Incoming record and retrieved prior render side by side
- [ ] Classification label and rationale visible
- [ ] Confidence bar visible
- [ ] **The pruning line reads: "Examined N of M records on this asset."** with real numbers ← *if this is missing, nothing else matters*
- [ ] Accept removes the item and writes a `SUPERSEDES` edge
- [ ] Opening a queue item does **not** change `maintenance_record_count`

### Diagnostics
- [ ] Aircraft selector lists real airframes
- [ ] Query returns ranked checks
- [ ] Evidence cites **only** real FAA IDs (`SWIA*`, `AALA*`, `VNAA*`) — **no `DEMO*`**
- [ ] No `[UNVERIFIED:...]` markers anywhere
- [ ] Context line states real counts
- [ ] Rare cases section expands

### Both themes
- [ ] Every page above checked in dark **and** light mode

---

# PART 3 — Slide deck with speaker script

Ten slides. Script is what you say, not what goes on the slide.

---

### Slide 1 — Title
**On slide:** Halite — Confidence-Gated Conflict Resolution over Evolving Institutional Records. Team, supervisor, **Stream B (application-derived)**.

> "Halite. Our supervisor is Syed Muhammad Saad Salman. We're declaring Stream B — the idea started from an observed workflow failure, not from a paper."

---

### Slide 2 — The problem, in one real example
**On slide:** the two 6704Z records side by side.

Record 1: *slide light won't extinguish → lubed girt bar*
Record 2, same aircraft, same day: *slide light won't extinguish. **Check history.** → found debris on proximity sensor*

> "Same aircraft, same fault, same day. The first technician lubricated a girt bar. That was wrong — the actual cause was debris on a proximity sensor. Nothing in the FAA's file connects these two records. They sit 200 rows apart. The only link is a technician writing 'check history' — an instruction to a human being, because no system would do it for them."

---

### Slide 3 — How often this happens (your strongest slide)
**On slide:** 65.2% / 42.6% / 47.5%, N = 141.

> "We measured it. Of 141 corrections in FAA Service Difficulty Reports where a later report supersedes an earlier one, 65.2% name a different component than the original. Two thirds of the time the follow-up blames something else entirely. To be precise: this is the rate among corrections we can observe — records where nobody filed a follow-up are invisible to us. It's still a measured rate of first-diagnosis re-attribution in a regulated system where every record was filed by a licensed mechanic."

---

### Slide 4 — What nothing currently does
**On slide:** four failures — search returns superseded records as top hits; wrong root causes stay on file; fleet patterns invisible; "check history" is unactionable at scale.

> "Search ranks by topic. A superseded record is maximally similar to its own subject, so it ranks high. Nothing marks it as overtaken. And on one airframe with 153 records, 'check history' means read all of them."

---

### Slide 5 — Why a graph (not storage)
**On slide:** 153 records → 11,628 all-pairs comparisons → 25 scored candidates. And 77.8% of records have no comparable prior at all.

> "Consistency checking is inherently pairwise. On our largest airframe, all-pairs is 11,628 comparisons per record. The graph constrains candidates to one asset's timeline, then scores by part, system code, location and recency — down to at most 25. And 78% of records have no comparable prior at all, so they never reach the model. The graph isn't where we put the data. It's what makes the comparison affordable."

---

### Slide 6 — The pipeline
**On slide:** Extract → Prune (graph) → Classify → Adjudicate → Confidence gate → Auto-apply or Review.

> "Adjudication takes no user input — it's computed from recency, source authority, explicit supersession language and part agreement. The gate decides whether we act or ask a human. And classification overrides confidence: a `contradicts` or `partial_supersedes` result never auto-applies at any confidence, because an unresolved contradiction is not a resolution."

---

### Slide 7 — Results
**On slide:** the comparison table.

| | Precision | Recall | F1 | False-conflict rate |
|---|---|---|---|---|
| Baseline (most-recent-prior) | 0.380 | 0.908 | 0.536 | **1.000** |
| Engine (t=0.50) | **0.903** | 0.660 | **0.762** | **0.048** |

> "Ground truth is author-recorded: the FAA writes 'supplemental report for' plus a record ID. We strip that citation before the pipeline sees it, so the system never reads the answer key. At pair level we recover 61% of the 141 known supersessions at 80% precision."

---

### Slide 8 — Why the baseline fails
**On slide:** baseline FP = 209 of 209.

> "The obvious baseline is 'assume the most recent prior record.' It has 0.908 recall — but it flags a conflict on every record it sees. On 209 negative pairs it asserted 209 supersessions that don't exist. False-conflict rate 1.000. It cannot abstain. In a system writing to aircraft maintenance records, a false supersession silently invalidates a real service record. We're wrong on 4.8% of negatives instead of 100%."

---

### Slide 9 — Method discipline
**On slide:** the pre-registered gate.

> "We planned to mine component dependency edges from corrections. We wrote the thresholds into the specification before running the measurement: at least 30% different-part corrections, and at least 10 component pairs with support of 3 or more. We got 65.2% on the first — and one component pair on the second. It failed, so we dropped the feature and recorded it. We think that's the right way to run a project, and it's why we trust the numbers that did pass."

---

### Slide 10 — Scope and what's next
**On slide:** FYP-1 committed / FYP-2 / dropped.

> "Committed: improve recall from 0.61 — that's the core FYP-1 work. Calibrate the confidence function properly on held-out data. Scale the corpus to more SDR years, which should also revisit the dependency gate. Explicitly out of scope: parts-demand forecasting, because SDRs are defect reports, not consumption records, and any forecast from them would be biased by reporting requirements while looking authoritative."

---

# PART 4 — Demo runbook

Two paths. Rehearse both. Screen recording on the presenting laptop as backup.

### Pre-flight, the morning of
```bash
docker compose up -d neo4j && sleep 60
# start backend, confirm:
curl -s localhost:8000/api/health | python -m json.tool
# graph_mode: neo4j, llm_mode: live, record count ~2079
python halite_check.py     # expect 0 FAIL
```
Pre-warm the diagnostic cache for `813SK`, `508AE`, `860NW`.

### Path A — Software domain (3 min)
1. Ingest a meeting transcript → decision extracted
2. Decisions page shows it
3. Trigger invalidation → alert appears
4. Chat cites the decision
5. Node visible in the 3D graph

### Path B — Maintenance (6 min)
1. **Switch domain.** Pause here. *"Same app, same graph, same engine. Different adapter."*
2. Assets → open `813SK`, 153 records
3. Scroll the timeline; point at a superseded record
4. Submit a real record (fresh ID, citation stripped)
5. **Say the pruning line out loud:** *"It examined 25 of this aircraft's 153 records."*
6. Show classification, rationale, confidence, route
7. Review Queue → open a case → Accept → `SUPERSEDES` edge appears in graph
8. Diagnostics → symptom on `813SK` → ranked checks with real FAA citations
9. Show `evaluation_results.md` — the measured numbers

### If the slot is 8 minutes
Cut A3, A5, then A4. **Never cut B1, B5, B7 or B9.**

### If a 429 hits
Cached results answer without a live call. If it still fails, switch to the recording and narrate. Do not present the error as a feature.

---

# PART 5 — Questions you will be asked

**"Why not just use the most recent record?"**
> Because it can't abstain. False-conflict rate 1.000 — on 209 negatives it claimed 209 supersessions that don't exist. Ours is 0.048.

**"Recall is only 0.61. Isn't that low?"**
> Yes, and it's our headline FYP-1 objective. We chose to be precise and abstain rather than aggressive and wrong, because a false supersession corrupts a real maintenance record. Improving recall without giving up precision is the work.

**"Isn't this just an LLM wrapper?"**
> The model classifies one pair. Which pairs are worth examining, how the winner is adjudicated, how confidence is computed, and whether we act — none of that is the model. Swap the model and the contribution survives. On our largest asset the model sees at most 25 of 11,628 possible pairs, and 78% of records never reach it.

**"How do you know your ground truth is right?"**
> We didn't write it. The FAA does — technicians file "supplemental report for" plus a record ID. We strip that citation before the pipeline sees the record.

**"What if the model hallucinates a record ID?"**
> Every cited ID is validated against the graph before the response returns. Invalid IDs are flagged, not shown as fact.

**"Your two models disagreed on your demo record."**
> They did — one said `contradicts`, the other `scope_disjoint`. It's in our limitations section with both rationales. Classifier stability is a known weakness and part of FYP-1.

**"Why two domains?"**
> One core mechanism, two adapters. The second domain is the control — if it works on formal software decision records and on terse field maintenance text with only the adapter changed, the mechanism is domain-independent rather than fitted to one corpus.

**"Where's the complex computing problem?"**
> In the constraints. Multiple sources that disagree, correctness with real consequences, auditability, and a system that must know when not to act. If the corpus were clean, every author annotated supersession by hand, and being wrong cost nothing, this wouldn't be hard.

**"Is your threshold overfitted?"**
> Performance is flat from 0.10 to 0.50 — F1 between 0.756 and 0.762 — so the choice isn't knife-edge. It collapses above 0.60. Proper calibration on held-out data is FYP-1.

---

# PART 6 — Before you present

- [ ] Revoke the Groq key that was shared in plain text; generate a new one
- [ ] Fix the "Partial run" header — N=350 is the complete deduplicated set over all 141 pairs
- [ ] Confirm the review queue count and the `SUPERSEDES` edge count from the graph; use those numbers everywhere
- [ ] Every document agrees on threshold 0.50 and model `openai/gpt-oss-120b`
- [ ] Screen recording of both paths on the presenting laptop
- [ ] Aura or local Neo4j awake and verified the night before
- [ ] Each team member can explain their own component without reading from code
