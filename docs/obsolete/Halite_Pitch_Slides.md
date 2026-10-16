# Halite — Proposal Defense Slides

Content for each slide, per the required 10-slide structure. Keep slides sparse — numbers, tables, diagrams. The talking happens in `Halite_Pitch_Script.md`, not on screen.

Scope note baked into every slide below: **this pitch presents the maintenance domain as the primary, evaluated system.** The software/decision-record domain exists in the same codebase on the same core pipeline (mentioned once, on Slide 6, as evidence the mechanism generalises) but is not the evaluation story tonight.

---

## Slide 1 — Title and one-line problem

**Halite**
Confidence-Gated Conflict Resolution over Evolving Maintenance Records

Team: Shahmeer Atif (23i-0711) · Muhammad Umar (23i-0782) · Muhammad Usman Al Haq (23i-0585)
Supervisor: Syed Muhammad Saad Salman
**Stream B — application-derived**

> One-line problem: *Maintenance organisations file corrective records that silently contradict earlier records on the same asset, and nothing today detects it automatically.*

---

## Slide 2 — Problem and users

**Real example — tail 6704Z, same aircraft, same day:**

| Record | Discrepancy | Action taken |
|---|---|---|
| 1st report | Slide light won't extinguish | Lubricated girt bar |
| 2nd report (same day) | Slide light won't extinguish — "check history" | Found debris on proximity sensor (actual cause) |

The two records sit ~200 rows apart in the FAA file. Nothing links them except a technician's instruction to another human: *"check history."*

**Stakeholders and current workflow:**

| Stakeholder | Today | Cost of failure |
|---|---|---|
| Field technician | Writes a terse record, assumes reader knows asset history | Repeats or misdiagnoses a known issue |
| Records supervisor | Manually reconciles a new record against paper/PDF history when something looks off | Incorrect service history; compliance exposure |
| Auditor / regulator | Reads the corpus, must establish what was true and when | Cannot reconstruct what the organisation actually knew |

**Current workflow, plainly stated: nobody checks. Contradictions surface only when someone acts on the wrong record.**

---

## Slide 3 — Existing solutions and prior-FYP comparison

| Existing approach | Core mechanism | Evidence-based limitation |
|---|---|---|
| CMMS / work-order platforms | Structured record storage, scheduling | Store records; never evaluate whether a new record contradicts stored history |
| RAG / retrieval assistants over records | Chunk → embed → retrieve top-k → generate | Retrieval ranks by topical similarity. A superseded record is maximally similar to its own subject — it ranks *high*, not low |
| Manual "check history" instruction | A technician tells the next reader to look | Unenforceable at scale — one asset in our corpus carries 153 records |
| Closest prior-FYP pattern: RAG chatbot over documents | Retrieval wrapper | Named directly in the FYP guide (§15) as a weak pattern where the central capability is supplied by the model, not the group |

**The gap, stated precisely:** no available system detects, adjudicates, and acts on conflicting maintenance records without a human reading every candidate pair by hand.

---

## Slide 4 — R&D and recent technical work

**What we ruled out, with evidence:**
- MaintNet aviation dataset — inspected directly: no asset ID, no date, mean 13.5 words/record. Cannot support per-asset history. **Dropped.**

**What we adopted, with evidence:**
- FAA Service Difficulty Reports — ~1.7M public-domain records; confirmed fields `RegistryNNumber` (tail number), `DifficultyDate`, `PartName`, `JASCCode`, free-text `Discrepancy`. Records naturally self-reference ("SUPPLEMENTAL REPORT FOR…", "CHECK HISTORY").

**Technical foundations applied:**
- Self-consistency majority voting for LLM classification stability (Wang et al., 2022, *Self-Consistency Improves Chain of Thought Reasoning*, arXiv:2203.11171) — 5-pass majority vote per classification, not a single call.
- Graph vs. relational performance for multi-hop, index-free traversal (Şensert et al., 2022, *Performance of Graph and Relational Databases in Complex Queries*, MDPI) — informs why candidate pruning is graph-native rather than a filtered SQL join.

---

## Slide 5 — Complex computing challenge

**The test we apply to ourselves (FYP guide §B.2):** *if the corpus were clean, every technician annotated supersession by hand, and being wrong cost nothing — would this still be hard?* **No.** Which is exactly why the constraints below, not the features, carry the CCP claim.

| Seoul Accord characteristic | Evidence in the built system |
|---|---|
| Conflicting requirements | Automation coverage vs. correctness, coded directly into the confidence gate — `contradicts`/`partial_supersedes` never auto-apply at any confidence |
| Depth of knowledge | JASC taxonomy, source-authority hierarchy, LLM self-consistency, confidence calibration |
| Unfamiliar issues | Calibrating a threshold with no held-out set; two models disagreeing on the same real pair |
| Significant consequences | A false auto-accept silently corrupts a real, regulator-facing aviation record |
| Interdependence | Pruning score → classification → adjudication → confidence → routing → graph write — a real, inspectable chain |
| Ill-defined requirements | "Does record B supersede record A" is not crisp — evidenced by our own two classifiers disagreeing on one real pair |

*Present, not yet strongly evidenced:* diverse stakeholders (no confirmed records-supervisor contact yet — named honestly, not hidden) and "beyond standard practice" for the exact pipeline as shipped today (the calibration/weighting problem is where the real difficulty sits, not any single stage in isolation).

---

## Slide 6 — Proposed solution and contribution

**Contribution statement:**
> Existing systems either require a human to manually mark a record as superseded, or retrieve by topical similarity with no notion of "still in force." We contribute a pipeline that automatically prunes candidate conflicting records using the asset graph, classifies the conflict type, adjudicates the winner from evidence signals (not user input), and gates every automatic action behind a calibrated confidence threshold — evaluated against 141 author-recorded FAA supersession pairs.

**Pipeline:**

```
Ingest → Graph-constrained candidate pruning → LLM classification (5-pass majority vote)
      → Evidence-based adjudication → Confidence gate → Auto-apply | Human review queue
```

**Architecture note:** this pipeline runs on a domain-adapter core — the same mechanism already runs a second, software decision-record domain in the shipped codebase with only the adapter swapped, which is why the pruning/classification/adjudication logic is not fitted to FAA text specifically.

**External components, classified per guide §14:** Neo4j = support. Groq LLM = core-assist (justified — no local model runs at required quality within team resources; outputs validated, fallback path implemented, contribution independent of model choice). Nothing is core-replacement.

---

## Slide 7 — POC-lite / feasibility evidence (mandatory — shown, not described)

**Live, not slides:** submit a record on tail `813SK` → pruning line reads *"examined 25 of 153 records"* → classification + rationale + confidence shown → routed to auto-apply or review queue → graph updates in real time.

**Pre-registered measurement that failed, and was honestly dropped:**

| Test | Threshold set in advance | Result | Decision |
|---|---|---|---|
| Component-transition mining (G0/G2) | ≥30% different-part corrections AND ≥10 component pairs at support≥3 | 65.2% different-part (passed) / only 1 pair at support≥3 (failed) | Extension **dropped**, recorded — not built, not claimed |

**What this proves:** the misdiagnosis-density measurement (65.2% of 141 corrections name a different component than the original report) — the load-bearing fact behind the whole CCP claim — is real, measured, and pre-registered before we saw the result.

**System status right now:** 2,079 real FAA records ingested, 121 conflicts detected, live against Neo4j — not a mockup.

---

## Slide 8 — Evaluation plan and risks

**Results so far (N=141 ground-truth pairs, 209 sampled negatives; model `openai/gpt-oss-120b`):**

| System | Precision | Recall | F1 | False-conflict rate |
|---|---|---|---|---|
| Baseline (assume most-recent-prior) | 0.380 | 0.908 | 0.536 | **1.000** |
| Halite engine (t = 0.50) | **0.788** | 0.660 | **0.762*** | **0.048** |

*F1 computed on the N=350 candidate-level set (141 positive + 209 negative): precision 0.903, recall 0.660.*

**Why the baseline is the wrong answer despite higher raw recall:** it cannot abstain — 209 of 209 negatives were false alarms. Ours is wrong on 4.8%.

**Threshold behaviour:** F1 flat (0.756–0.762) across thresholds 0.10–0.50; collapses above 0.60 — the choice is not knife-edge, but proper held-out calibration is committed FYP-1 work, not a claimed result.

**Top risks (RAID):**

| Risk | Mitigation |
|---|---|
| Recall (0.66) leaves real supersessions in the corpus unflagged | Headline FYP-1 objective; only the #1 heuristic-ranked candidate is currently classified — extending to top-k is the named fix |
| No confirmed records-supervisor stakeholder yet | POC-0 style outreach in progress; proxy will be declared explicitly if not secured, not discovered at final defense |
| LLM rate limits on a free-tier model | Caching + retry queue already implemented; degraded mode routes safely to review, never fabricates |
| Confidence threshold calibrated on a small set historically | Full N=350 rerun now in place; held-out recalibration is committed FYP-1 work |

---

## Slide 9 — Work division and iteration plan

| Member | Primary technical ownership |
|---|---|
| Shahmeer Atif | Evidence-based adjudication, confidence calibration, review-queue integration |
| Muhammad Umar | Graph-constrained candidate pairing, conflict classification, graph schema |
| Muhammad Usman Al Haq | Domain adapter, corpus acquisition/labelling, evaluation harness, deployment |

**Removal test:** removing any one member removes an entire pipeline stage, the evaluation basis, or the deployment path — no member owns only UI or documentation.

**Milestones:**

| Stage | Deliverable |
|---|---|
| FYP-1 Mid | Requirements/design baselined; top-k candidate classification implemented; SRS submitted |
| FYP-1 Final | Recalibrated confidence gate on held-out split; recall improvement measured against today's 0.66; SDS submitted |
| FYP-2 Mid | Full evaluation harness vs. all baselines; NFRs measured; ≥80% backend test coverage |
| FYP-2 Final | Stakeholder UAT completed; deployed and operable by an outsider from the README; final report set |

---

## Slide 10 — DEI, ethics and legal issues

**DEI statement:** the system evaluates records, not people — no technician is scored, ranked, or individually flagged. The review-queue UI targets WCAG AA contrast and full keyboard navigation so any authorised reviewer, including those using assistive technology, can operate it equally.

**Ethical statement:** FAA Service Difficulty Report data is US public-domain and contains no personal identifying information about individuals. The system never silently edits a record — every automatic action is logged and reversible, and ambiguous or high-severity cases are routed to a human, not resolved autonomously, precisely because automation bias in a safety-relevant record system is an ethical risk we designed against, not an afterthought.

**Legal / compliance:** Groq API usage complies with its published terms; no scraping or unauthorised data collection; AI-assisted development disclosed at Level 2 per guide §8, with an AI usage log maintained and updated as work proceeds, not reconstructed after the fact.
