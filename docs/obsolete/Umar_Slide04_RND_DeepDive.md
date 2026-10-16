# Slide 04 Prep — R&D / Recent Technical Work (Umar)

Plain-language deep dive. Learn this until you can explain each box without the slide.

**Your one job on this slide:** show you looked for people who already solved *record-vs-record conflict in maintenance*, and nobody did. Then close with the gap Halite fills.

**One sentence for the whole slide:**
> "Others store, retrieve, classify one report, or find conflicts in clean structured graphs. Nobody automatically finds when a new free-text maintenance report proves an older one wrong."

---

## How to speak the slide (45–60 seconds)

> "We went looking for whoever already solved this.
>
> First, a 2025 systematic review of knowledge graphs in industrial maintenance screened 270 papers and studied 76. The uses they found are fault diagnosis, choosing a repair action, and organising maintenance work. Record consistency — marking an old report as no longer true — is not one of those categories.
>
> Second, the closest aviation system to us is KEO from Notre Dame, October 2025. It builds a knowledge graph from aviation maintenance text and uses it with RAG so an AI can answer questions. We read the full paper. The words conflict, contradict, and supersede do not appear. It answers questions. It does not mark old records invalid.
>
> Third, PaTeCon from AAAI 2023 does detect conflicts on knowledge graphs — but only on clean structured facts in Wikidata and Freebase, where a hard time rule can be broken. Our reports are free text. They have no such hard rules.
>
> Fourth, Boeing and the FAA already work our exact corpus — Service Difficulty Reports — but they classify one report for hazard type. Fire, engine, structure. Never report against report.
>
> So the gap is open: compare records, and decide what is no longer true."

---

# Paper 1 — Industrial maintenance KG systematic review

### Full name / citation
**Knowledge graphs for operational decision-making in industrial maintenance: A systematic review**  
Wang et al., *Expert Systems with Applications*, 2025  
DOI: https://doi.org/10.1016/j.eswa.2025.130172

### Purpose (what they tried to do)
Answer three questions about knowledge graphs in day-to-day industrial maintenance:
1. How are KGs used to help decisions?
2. In which scenarios are they used?
3. What challenges remain in real practice?

### Environment / setup
- Searched **Scopus**
- **270** papers retrieved after first screening
- **76** papers examined in detail
- Domain: industrial / operational maintenance (factories, equipment), not specifically our FAA SDR pipeline

### What they found (parameters / results in plain words)
Common KG methods:
- **Querying** the graph
- **Reasoning** on the graph
- **Helping other algorithms** (using the graph as extra knowledge)

Common application areas (three buckets — matches your slide):
1. **Fault diagnosis** — what is broken?
2. **Maintenance action identification** — what should we do?
3. **Maintenance organization** — how do we plan / structure the work?

They also note most real uses are still limited to fairly simple tasks, and sharing/scaling KGs is still hard.

### How it relates to Halite
- Proves the field cares about maintenance + knowledge graphs.
- Also proves the field’s usual goals are **diagnose / act / organise**.
- **Missing category:** keeping the *record set consistent* when later reports overturn earlier ones.

### If a panelist asks
**Q: Did you invent this gap?**  
A: No. This review maps what KG-maintenance papers actually do. Consistency of evolving records is not listed among the main uses.

**Q: Are you saying KGs are useless then?**  
A: No. We also use a graph — but for a different job: cutting comparisons to the same aircraft and linking supersession. The review shows that *job* was not the focus of prior maintenance KG work.

---

# Paper 2 — KEO (closest work to yours)

### Full name / citation
**KEO: Knowledge Extraction on OMIn via Knowledge Graphs and RAG for Safety-Critical Aviation Maintenance**  
Ai, Karr, Jiang, Chawla, Wang — University of Notre Dame  
arXiv:2510.05524 (Oct 2025)  
Code: https://github.com/JonathanKarr33/keo

### Purpose
Help AI systems answer questions over aviation maintenance data in a **safe, local** way (no sending secret data to outside APIs).

Two kinds of questions they care about:
1. **Global sensemaking** — “what patterns exist across many records?”
2. **Knowledge-to-action** — “given a problem, what action makes sense?”

### Environment / data
- Dataset: **OMIn** (Operations and Maintenance Intelligence)
- OMIn = **2,748** short FAA **Accident/Incident** maintenance-related records (not the full SDR dump Halite uses, but same aviation world)
- Typical record: about **1–3 short sentences**, mean length ~17 words
- They build a knowledge graph from a sample of records, then plug that graph into **RAG** (retrieve useful context, then generate an answer)
- Local answer models they tested: Gemma-3, Phi-4, Mistral-Nemo
- Stronger models (GPT-4o, Llama-3.3) used as **judges**, not as the main answer engine
- Benchmark: **133 questions** (83 global + 50 action-style)

### Important results (simple)
- For **big-picture / pattern** questions → KEO (graph + RAG) beats normal text-chunk RAG
- For **local procedural / action** questions → normal text RAG is often still better
- Their own conclusion: different retrieval styles help different tasks

### How it relates to Halite
| | KEO | Halite |
|---|---|---|
| Domain | Aviation maintenance | Aviation maintenance (SDR) |
| Uses KG? | Yes | Yes |
| Uses LLM? | Yes | Yes |
| Main goal | Answer questions | Detect when a new report overrides an old one |
| Marks old records untrue? | No | Yes (SUPERSEDES) |
| Needs abstention / confidence gate? | Not their focus | Core of the design |

**This is why you call it “closest but still not us.”** Same neighbourhood. Different problem.

### About “conflict 0 · contradict 0 · supersede 0”
Your slide claim: you searched the full paper text for those words and found none.

Be ready to say:
> “We checked the full paper for conflict, contradict, and supersede. Those terms do not appear. Their framing is question answering and pattern discovery, not record invalidation.”

If someone finds a near-synonym (“inconsistency,” “stale,” etc.), do not panic. Your point is still: **their system is built to answer, not to adjudicate supersession between two filed reports.**

### If a panelist asks
**Q: So aren’t you just copying KEO?**  
A: No. KEO retrieves and answers. We prune candidate pairs, classify conflict type, then decide whether to mark an older report overridden — or abstain to a human.

**Q: Same dataset?**  
A: Same *domain*, not the same file. KEO uses OMIn (2,748 accident/incident maintenance texts). We use FAA Service Difficulty Reports with tail numbers and dates so we can do per-aircraft history.

**Q: Why mention KEO at all?**  
A: Because it is the strongest nearby aviation KG+LLM system. If *even that* does not do record-vs-record supersession, the gap is clearer.

---

# Paper 3 — PaTeCon

### Full name / citation
**PaTeCon: A Pattern-Based Temporal Constraint Mining Method for Conflict Detection on Knowledge Graphs**  
Chen, Ren, Ding, Qu — AAAI 2023  
https://doi.org/10.1609/aaai.v37i4.25533  
arXiv: https://arxiv.org/abs/2304.09015

(There is also a later extension paper about faster mining and new conflict benchmarks — same family.)

### Purpose
Automatically find **time conflicts** in large knowledge graphs — without humans writing all the rules by hand.

Example of the kind of conflict they care about:
- A person cannot be in two jobs at overlapping impossible times
- An event’s end time cannot be before its start time
- Two facts that break a learned time pattern

### Environment / data
- Structured KGs: **Wikidata** and **Freebase**
- Datasets discussed: WD50K, larger sets like WD27M / FB37M
- Facts are already in clean form: entity–relation–entity, often with time stamps / time intervals
- Method mines **temporal constraints** from graph patterns + statistics, then uses those constraints to flag conflicts

### Parameters / idea in plain words
1. Look at common patterns of time facts in the graph
2. Measure how often a pattern holds
3. Turn strong patterns into constraints
4. Flag facts that break those constraints

### How it relates to Halite
PaTeCon proves: **conflict detection on graphs is a real research problem.**

But it needs:
- already-structured RDF-style facts
- a **hard constraint** that can be violated

Halite’s world:
- messy free-text technician reports
- no neat “start_time / end_time” schema on the sentence
- conflict is semantic (“this diagnosis replaces that one”), not only temporal rule breaking

So PaTeCon is useful as a cousin, not a competitor that already solved your problem.

### If a panelist asks
**Q: Conflict detection already exists — PaTeCon.**  
A: Yes, on structured knowledge graphs with hard time rules. Our inputs are free-text service reports. They do not arrive as RDF quadruples with constraints ready to violate.

**Q: Could you convert reports into RDF and then use PaTeCon?**  
A: Extraction into perfect structured facts is itself hard (KEO’s own related OMIn work shows NLP tools struggle on this domain). Even then, supersession between diagnoses is not the same as a temporal constraint violation. We would still need a validity / adjudication stage.

---

# Work 4 — Boeing + FAA SDR hazards classification

### Full name / source
**Boeing / FAA — sdr-hazards-classification**  
Public GitHub: https://github.com/Boeing/sdr-hazards-classification  
PyPI package available; v1.0.0 around May 2024

### Purpose
Help safety analysts spot **hazard types** inside SDR free text for Continued Operational Safety (COS) work.

Examples of hazard labels: fire, depressurization, abnormal vibration, structure, engine, fuel, runway excursion, flight crew, etc.

### Environment / data
- Exact family of data Halite uses: **FAA Service Difficulty Reports**
- Free-text discrepancy fields: messy, abbreviations, part numbers, typos
- Experts annotated hundreds of SDRs per hazard model for training/testing
- Models: classical ML style (package depends on pandas, scikit-learn, xgboost) — not a KG conflict engine

### What it does / does not do
Does:
- Take **one** report’s text
- Predict whether it matches a hazard criterion

Does not:
- Compare report A to report B
- Decide that report B overrides report A
- Mark older history as superseded

### How it relates to Halite
This is gold for your defense because it blocks a bad panel question:

**“Isn’t FAA/Boeing already doing AI on SDR?”**  
Answer:
> “Yes — and we looked at it. They classify one report for hazard type. We compare reports on the same aircraft over time. Same corpus, different question.”

### If a panelist asks
**Q: Why not just use Boeing’s models?**  
A: Different output. Hazard class ≠ supersession link. We can coexist: their models label risk type; we maintain record validity over time.

**Q: Same data proves nothing is left to do?**  
A: Opposite. It proves the corpus is industrially important, and still leaves record-vs-record consistency unsolved.

---

# Optional 5th reference (recommended if you have room)

You do **not** must add this to the slide. Learn it as backup ammunition.

### MemStrata — Temporal Validity in Retrieval Memory (2026)
arXiv: https://arxiv.org/abs/2606.26511

**Purpose:** show that normal RAG cannot tell a current fact from a superseded fact, because both look similarly “relevant.”

**Key plain finding:** embedding similarity is near chance at separating “contradicted” vs “duplicate” facts. When forced to answer, RAG serves the old wrong value a large fraction of the time.

**Their fix:** deterministic supersession on clean (subject, relation, object) facts — retire the old value when a newer assertion changes it.

**Relation to Halite:**
- Supports your Slide 03 claim: retrieval ranks by similarity, not by “still true.”
- Different from you: they assume clean structured facts and a hard supersession rule. You work on messy free-text maintenance reports and need classification + confidence gate + human review.

**When to mention:** only if someone says “RAG already solves evolving knowledge.”

Say:
> “Recent work like MemStrata shows RAG has a structural stale-fact problem. Their fix needs clean triples. Our reports are free text, so we still need candidate pruning, conflict labels, and a confidence gate.”

---

# The comparison table (memorize this)

| Work | Year | What they do | What they do **not** do | Link to Halite |
|---|---|---|---|---|
| Maintenance KG review | 2025 | Map KG uses in maintenance | Record consistency as a main category | Shows gap in the literature map |
| KEO | 2025 | KG + RAG Q&A on aviation text | Mark old reports superseded | Closest neighbour; still QA not adjudication |
| PaTeCon | 2023 | Conflict detection on structured KGs | Free-text maintenance supersession | Same word “conflict,” different input world |
| Boeing SDR classifier | 2024 | One-report hazard classification | Report-vs-report comparison | Same corpus, different question |
| (backup) MemStrata | 2026 | Prove RAG fails on stale facts | Free-text maint. adjudication | Supports “retrieval ≠ validity” |

---

# What NOT to claim tomorrow

- Do not say “nobody ever used graphs in maintenance.” They did — for diagnosis/actions.
- Do not say “KEO is bad.” Say “KEO solves a neighbouring problem.”
- Do not say “PaTeCon is irrelevant.” Say “PaTeCon needs structured constraints we do not have.”
- Do not say “we invent contradiction detection.” Say “we apply conflict finding to evolving free-text service records with abstention.”
- Do not invent paper numbers. Stick to: 270/76, OMIn 2,748, KEO 133 questions, AAAI 2023, Boeing public repo.

---

# Tiny checklist before sleep

- [ ] Say the 60-second script once without looking
- [ ] Explain KEO vs Halite in one breath
- [ ] Explain PaTeCon’s “hard constraint” issue in one breath
- [ ] Explain Boeing “one report, not two” in one breath
- [ ] Remember optional MemStrata only as backup

You are solid on this slide when the gap sentence is automatic:
**store / retrieve / classify-one / structured-conflict ≠ free-text record supersession with abstention.**
