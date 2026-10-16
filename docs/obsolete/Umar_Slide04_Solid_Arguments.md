# Slide 04 — Solid Arguments Pack (Verified)

Everything below was checked against public sources (papers / GitHub / Cambridge repository / arXiv HTML). Use these as your backup facts. Do not invent beyond this list.

---

## The master argument (say this confidently)

Halite’s problem is **not**:
- “find similar past reports”
- “answer a question about maintenance”
- “label one report as fire / engine / depressurization”
- “find time conflicts in Wikidata”

Halite’s problem **is**:
> When a new free-text service report arrives for an aircraft, decide whether it **overrides / conflicts with** an older report on that same aircraft — and only act when we are confident enough.

Your four references prove that nearby work exists, but each one stops before that last step.

---

# 1) Systematic review — Kang et al., 2025

### Exact citation (verified)
**Kang, R., Zhu, J., Green, S., Brilakis, I.**  
*Knowledge graphs for operational decision-making in industrial maintenance: A systematic review*  
**Expert Systems with Applications**, Volume **299**, 2025, Article **130172**  
DOI: https://doi.org/10.1016/j.eswa.2025.130172  
Cambridge repository: https://www.repository.cam.ac.uk/items/bbb13add-4b11-4601-8476-92d9e6452b78

### What they did
A systematic literature review of knowledge graphs used for **operational maintenance decisions**.

### Verified numbers
- Search database: **Scopus**
- Access date noted in paper text: **4 March 2025**
- After first screening: **270** papers
- Closely examined: **76** papers

### What they asked (3 research questions)
1. What methods use KGs for maintenance decisions?
2. In which scenarios are KGs applied, and how?
3. What challenges/opportunities remain in practice?

### What they found (verified)
**Methods commonly used:**
- KG querying
- KG reasoning
- Using KGs to enhance other algorithms

**Scenarios / application categories:**
1. **Fault diagnosis** (most common) — what is wrong?
2. **Maintenance action identification** — what should we do?
3. **Maintenance organization** — scheduling / planning / grouping work

**Extra finding you can use:**
> Most applications are still limited to fairly simple tasks; more work is needed on efficiently using and sharing KGs in practice.

### Solid argument for Halite
This review is a map of the field. On that map, the main destinations are diagnose / act / organise.

**Record consistency** — “this later report makes that earlier report no longer trustworthy” — is **not** one of those three destinations.

So if a panelist says “knowledge graphs in maintenance are already saturated,” you answer:
> “Saturated for diagnosis and action support. Not for detecting when one filed report supersedes another.”

### Honest limit (say this if pressed)
This review is about industrial operational maintenance broadly, not only aviation SDR. That is fine. You are using it as a **field map**, not as “zero aviation papers exist.”

---

# 2) KEO — Ai et al., Notre Dame, Oct 2025 (closest neighbour)

### Exact citation (verified)
**Ai, K.; Karr, J.A.; Jiang, M.; Chawla, N.V.; Wang, C.** (University of Notre Dame)  
*KEO: Knowledge Extraction on OMIn via Knowledge Graphs and RAG for Safety-Critical Aviation Maintenance*  
arXiv:**2510.05524** (submitted ~7 Oct 2025)  
HTML: https://arxiv.org/html/2510.05524  
Code: https://github.com/JonathanKarr33/keo

### Purpose
Build a **secure, local** KG + RAG system so smaller LLMs can answer aviation-maintenance questions without sending sensitive data to outside APIs.

### Environment / data (verified)
- Dataset: **OMIn** (Operations and Maintenance Intelligence)
- OMIn source paper/dataset: Mealey et al., curated from FAA Accident/Incident data
- Size: **2,748** short maintenance-related incident records
- Typical length: about **1–3 sentences**, mean ~**17 words**
- Safety framing: prefer local models; avoid external APIs for the live answer path

### Their pipeline (plain)
1. Extract entities/relations from maintenance text
2. Build a knowledge graph
3. Use that graph inside RAG
4. Ask questions and generate answers

### Their evaluation setup (verified)
- Benchmark: **133 questions**
  - **83** global sensemaking (patterns across the corpus)
  - **50** knowledge-to-action style questions
- Answer models tested locally: **Gemma-3, Phi-4, Mistral-Nemo**
- Judges (not the main answerers): **GPT-4o, Llama-3.3**
- KG construction detail: they sample **500 / 2,748** OMIn records for graph construction in the reported setup

### Their result (verified, simple)
- On **global / pattern** questions → KEO (graph-RAG) beats plain text-chunk RAG
- On **local procedural / action** questions → plain text RAG is often still competitive or better
- Their own conclusion: different retrieval styles help different tasks

### Word-count claim — RE-VERIFIED by us on the arXiv HTML text
In the KEO paper text we checked:
- `conflict` = **0**
- `contradict` / `contradiction` = **0**
- `supersede` / `superseded` = **0**
- `stale` = **0**
- `invalidate` / `override` = **0**

There **are** 2 mentions of `inconsistencies` / `inconsistency` — but only in the general sense that KGs help reduce LLM **factual inconsistency / hallucination**.  
That is **not** “detect when report B supersedes report A.”

**How to say this safely:**
> “We checked the paper for conflict, contradict, and supersede — zero hits. The two ‘inconsistency’ mentions are about LLM factual grounding, not record-vs-record supersession.”

### Solid argument for Halite
KEO is your strongest neighbour because:
- same domain family (aviation maintenance text)
- also uses KG + LLM
- also cares about safety-critical trust

But KEO’s success metric is **answer quality on questions**.  
Halite’s success metric is **whether an older filed report should be marked overridden**, with abstention when unsure.

| | KEO | Halite |
|---|---|---|
| Main output | Answers to questions | Conflict labels + SUPERSEDES decisions |
| Graph used for | Better retrieval / sensemaking | Candidate pruning + validity links |
| Marks old records untrue? | No | Yes |
| Needs confidence gate / human review path? | Not the core claim | Core claim |
| Dataset | OMIn (2,748 AID maintenance texts) | FAA SDR corpus with tail + date |

### Extra solid point: different source files
OMIn ≠ full SDR dump.
- OMIn = maintenance-related subset of FAA **Accident/Incident** descriptions
- Halite = **Service Difficulty Reports** (defect/malfunction filings with registry/tail numbers)

Same industry language. Different operational record stream. Do not claim “identical dataset.” Claim “same domain, different corpus and different task.”

### If attacked: “You are just GraphRAG”
Answer:
> “GraphRAG answers. We adjudicate validity. If KEO retrieves both an old wrong diagnosis and a later correction, nothing in KEO’s design requires marking the old one superseded. That is exactly the step we add.”

---

# 3) PaTeCon — Chen et al., AAAI 2023

### Exact citation (verified)
**Chen, J.; Ren, J.; Ding, W.; Qu, Y.**  
*PaTeCon: A Pattern-Based Temporal Constraint Mining Method for Conflict Detection on Knowledge Graphs*  
Proceedings of the AAAI Conference on Artificial Intelligence, **37**(4), 4166–4172, 2023  
DOI: https://doi.org/10.1609/aaai.v37i4.25533  
arXiv: https://arxiv.org/abs/2304.09015  
Code: https://github.com/JianhaoChen-nju/PaTeCon

### Purpose
Automatically mine **temporal constraints**, then use them to detect **temporal conflicts** in large knowledge graphs — without humans writing every rule.

### Concrete example from their paper (easy to remember)
Wikidata has two overlapping “member of sports team” facts for the same person with incompatible time ranges.  
Humans recognise: those careers cannot both be true at once.  
PaTeCon tries to learn such rules automatically.

### Environment / data (verified numbers)
| Dataset | Entities | Facts | Notes |
|---|---|---|---|
| WD50K | 17,176 | 50,000 | small Wikidata sample for comparison |
| WD27M | ~7.2M | ~27.3M | Wikidata dump-based large set |
| FB37M | ~10.2M | ~37.9M | Freebase-based large set |

Input form: **RDF-style temporal facts** = quadruples `(subject, predicate, object, time-interval)`.

### Method parameters (verified)
They mine constraints using graph patterns + statistics.

Thresholds they report using:
- frequency threshold `θ_freq = 100`
- confidence thresholds `θ_c1 = 0.5`, `θ_c2 = 0.9`

Temporal predicates they use:
- start, finish, before, disjoint, include

Hardware they report:
- single-threaded Python
- Xeon CPU + 128GB RAM workstation

### Results worth remembering
- Against hand-crafted rules (Chekol et al. 2017) on WD50K: PaTeCon’s mined constraints were judged cleaner on granularity
- On large sets they mine hundreds of constraints and detect many possible conflicts (e.g. WD27M: **644** constraints, **703,715** possible conflicts)
- Important nuance: “possible conflicts” still need quality checking; not every flagged subgraph is a perfect real-world conflict

### Solid argument for Halite
PaTeCon proves conflict detection on graphs is real research.

But it needs all of this first:
1. facts already stored as clean RDF / temporal quadruples
2. explicit time intervals
3. a **hard constraint** that can be violated (disjoint careers, impossible ordering, etc.)

Halite starts from:
- messy free-text technician reports
- abbreviations, part numbers, shorthand
- semantic diagnosis changes (“girt bar” vs “proximity sensor”), not only impossible calendars

So PaTeCon cannot be dropped onto SDR text and “just work.”

### Strong one-liner
> “PaTeCon finds conflicts when structured facts break a time rule. Our reports are free text, and the conflict is often semantic supersession, not a broken calendar constraint.”

### If attacked: “Convert text to RDF, then use PaTeCon”
Good answer:
> “Extraction into perfect temporal facts is itself unsolved in this domain — OMIn/KEO-related work already shows NLP tools struggle on aviation maintenance shorthand. Even after extraction, ‘later diagnosis replaces earlier diagnosis’ is not the same as ‘two team memberships overlap illegally.’ We would still need pairing, semantic classification, and abstention.”

---

# 4) Boeing + FAA SDR hazard classification

### Exact sources (verified)
**Public engineering package**
- GitHub: https://github.com/Boeing/sdr-hazards-classification
- Explicitly: collaboration between **FAA and Boeing** data-science teams
- Goal: help Continued Operational Safety (COS) analysts

**Academic paper behind the depressurization work**
- Niraula et al., *Discovering Depressurization Events in Service Difficulty Reports using Machine Learning*
- 2023 IEEE International Conference on Prognostics and Health Management (ICPHM)
- DOI: https://doi.org/10.1109/icphm57936.2023.10194079
- IEEE: https://ieeexplore.ieee.org/document/10194079
- SKYbrary summary: reports F1 **up to 95%** for depressurization discovery

### What they do (verified from README + paper abstract)
- Input: **one** SDR free-text description
- Output: whether it matches a hazard / COS criterion
- Examples of criteria/models: depressurization, fire, structure, engine, fuel, runway excursion, flight crew, abnormal vibration, etc.
- SMEs annotated **hundreds** of SDR records per model
- Code exposes APIs like `get_predictions([event_text])` on a single text string / list of texts
- Stack in package: pandas, scikit-learn, xgboost (classical ML classifiers, not a conflict graph engine)

### Why this corpus is hard (their own words, useful to steal)
SDR free text:
- no predictable grammar
- not standardized
- typos
- part numbers
- abbreviations
- references to manuals/procedures

That helps you: if Boeing/FAA needed ML just to label **one** messy report, comparing **two** messy reports over time is clearly harder, not already solved.

### Solid argument for Halite
This is your best “same data, different question” proof.

| | Boeing/FAA classifier | Halite |
|---|---|---|
| Corpus | FAA SDR | FAA SDR |
| Unit of analysis | One report | Pair of reports on same aircraft |
| Output | Hazard type / COS flag | Conflict type + possible SUPERSEDES |
| Industrial proof | Yes — public repo + IEEE paper | Our contribution sits after theirs |

### Strong one-liner
> “Boeing and FAA already prove SDR text is industrially important. Their system asks: what hazard is in this report? We ask: does this report overturn an earlier one?”

### If attacked: “Just reuse Boeing”
> “We can coexist. Hazard class does not tell you whether yesterday’s diagnosis is still valid after today’s supplemental report.”

---

# 5) Optional backup — MemStrata (2026)

Use only if someone says “RAG already handles evolving knowledge.”

### Citation
*Temporal Validity in Retrieval Memory...* (MemStrata), arXiv:2606.26511  
https://arxiv.org/abs/2606.26511

### Verified killer facts
- Cosine similarity separating contradiction vs duplicate: **AUROC ≈ 0.59** (near chance)
- On their calibration set, contradictions were **more similar** to the original than duplicates were
- When forced to answer, RAG serves superseded values **15–40%** of the time
- Their fix is deterministic supersession on clean `(subject, relation, object)` facts

### How to use it for Halite
Supports Slide 03/04 claim: retrieval ranks by similarity, not validity.

Then draw the boundary:
> “MemStrata needs clean triples and a hard supersession rule. Our technician text is not already in that form, so we still need candidate pruning, semantic conflict labels, and a confidence gate with human review.”

---

# Attack → Defense card (memorize)

| Panel attack | Your defense |
|---|---|
| “KG maintenance is already done” | Kang et al. map shows diagnosis/action/organisation — not record supersession |
| “KEO already did aviation KG+LLM” | KEO answers questions; we adjudicate whether old reports remain true |
| “Conflict detection exists (PaTeCon)” | Yes — on RDF temporal graphs with hard constraints, not free-text SDRs |
| “FAA/Boeing already do SDR AI” | Yes — one-report hazard classification; not report-vs-report validity |
| “This is just RAG” | RAG retrieves similar text; superseded text is often most similar. Validity is a different problem |
| “Why graph then?” | Not for storage fashion — to cut impossible cross-aircraft comparisons and attach SUPERSEDES links |

---

# What you can safely claim tomorrow

1. We surveyed the nearest maintenance-KG literature map (Kang et al., 270→76).
2. Closest aviation KG+LLM system (KEO) is Q&A-focused; conflict/contradict/supersede absent as task terms.
3. Structured KG conflict mining (PaTeCon) exists, but assumes RDF temporal constraints.
4. Same SDR corpus already used industrially by Boeing/FAA for single-record hazard classification.
5. Therefore Halite’s open gap is: **pairwise free-text record conflict + cautious adjudication**.

# What you should NOT claim

- “No one ever used graphs in maintenance.”
- “KEO is useless.”
- “PaTeCon cannot detect any conflicts.”
- “We are the first people to use LLMs on SDR.”
- “OMIn and SDR are the exact same dataset.”

---

# 70-second speaking version (more detailed)

> We looked for whoever already solved record-vs-record conflict in maintenance.
>
> First, Kang, Zhu, Green and Brilakis’ 2025 systematic review in Expert Systems with Applications screened 270 Scopus papers and examined 76. Knowledge graphs in maintenance are mainly used for fault diagnosis, choosing actions, and organising work. Record consistency is not one of those categories.
>
> Second, the closest aviation system is KEO from Notre Dame. It builds a knowledge graph from OMIn — 2,748 short FAA maintenance incident texts — and uses graph-RAG so local models can answer 133 benchmark questions. It helps global pattern questions. We checked the paper text: conflict, contradict, and supersede do not appear. It answers. It does not mark an old filed report as overridden.
>
> Third, PaTeCon at AAAI 2023 does detect conflicts — on Wikidata and Freebase temporal facts already stored as RDF quadruples, by mining hard time constraints. Our inputs are free-text service reports. They do not arrive with those constraints.
>
> Fourth, Boeing and the FAA already work our corpus. Their public SDR hazard classifiers — with an IEEE paper showing up to 95% F1 on depressurization discovery — classify one report for hazard type. Never report against report.
>
> So the remaining problem is ours: compare records on the same aircraft, decide the conflict type, and abstain when we are not sure.

---

Tonight: read this once, then close it and recite the attack→defense card out loud. That card is what wins Q&A.
