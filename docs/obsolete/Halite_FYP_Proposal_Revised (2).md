# Halite — Confidence-Gated Conflict Resolution over Evolving Institutional Records

**FYP Proposal (Revised)**

| Field | Value |
|---|---|
| Project title | Halite |
| Supervisor | Syed Muhammad Saad Salman |
| Team | Shahmeer Atif (23i-0711), Muhammad Umar (23i-0782), Muhammad Usman Al Haq (23i-0585) |
| Declared stream | **Stream B — application-derived** (see §1.3) |
| Primary SDG / thematic area | SDG 9 — Industry, Innovation and Infrastructure |
| Deployment target | Containerised backend on a VM/free-tier host; React frontend on Vercel; Neo4j as managed or containerised instance |

---

## 1. Problem

### 1.1 One-sentence statement

Organisations accumulate large bodies of written records that silently contradict one another over time, and no system detects when a newly recorded item supersedes, contradicts, or invalidates something already on file — so people continue to act on records that are no longer true.

### 1.2 What actually goes wrong

Every organisation that keeps a written record of its decisions faces the same failure. A decision is recorded. Months later a second decision is recorded that overrides part of the first. Nobody annotates the first. Both remain in the corpus, both are retrievable, both read as authoritative, and the reader has no way to tell which one still holds.

The failure has three distinct forms, and they need different handling:

1. **Supersession** — a later record replaces an earlier one, in whole or in part.
2. **Direct contradiction** — two records make incompatible claims about the same subject, and neither declares priority.
3. **Downstream inheritance** — a record was written using an earlier record as context. When that earlier record is later corrected or superseded, everything derived from it becomes suspect, and nothing marks it.

The third is the one no existing system addresses at all. It is not a retrieval problem; it is a consistency-maintenance problem over a stored corpus.

### 1.3 Two domains, one failure

The same failure appears in two settings the team can access, with real data and verifiable ground truth. This is why the project addresses both.

**Domain A — Software engineering decision records (primary).** Teams record architectural and design decisions in ADRs, RFCs, PEPs, meeting transcripts and pull-request discussions. Later decisions supersede earlier ones. In formal RFC processes the supersession is sometimes recorded in a status header; in most day-to-day records it is not recorded at all. Downstream documents written on top of a superseded decision are never revisited.

**Domain B — Maintenance and field-service records (secondary).** Technicians record what was found and what was done on a specific physical asset. Records reference prior work implicitly ("check history", "supplemental report for…", "see long history"). When a record is later corrected, later records that were written with the incorrect one as context are not revisited.

Domain A supplies verifiable ground truth and is therefore the primary evaluation setting. Domain B supplies a structurally different corpus that tests whether the mechanism is genuinely domain-independent, and supplies the second stakeholder group.

**The stream is declared as B — application-derived.** The idea originates from an observed workflow failure — organisations acting on records that are no longer true, with no system checking — rather than from a stated limitation in a published paper. The published work in §2.2 informs the design and the evaluation, but it is not where the idea began. Per guide §1.1, the stream states where the idea came from and which risk is tested first; it does not reduce what must be delivered.

Accordingly, the **first risk tested is not a method risk but an access and reality risk**: whether the problem is real to the people who face it, whether stakeholders will engage, and whether the required records can be obtained. §7 orders the proposal-stage evidence on that basis. The method risks are tested immediately after, because a Stream B project that cannot locate its complex computing problem fails just as surely (guide §B.4, "late discovery that there is no complexity").

### 1.4 Stakeholders and the current workflow

| Stakeholder | Domain | How the task is handled today | Consequence of failure |
|---|---|---|---|
| Software engineer / tech lead | A | Reads whatever decision record retrieval surfaces; relies on memory of who decided what and when | Implements against a superseded constraint; rework, architectural drift |
| Technical writer / new joiner | A | Reads the record set front to back; cannot tell current from obsolete | Propagates obsolete guidance into new documentation |
| Field technician | B | Writes a terse record assuming the reader knows the asset | Later reader misinterprets; repeat or wrong intervention |
| Office manager / records supervisor | B | Manually reconciles a new record against paper history when something looks off | Incorrect service history; warranty and compliance exposure |
| Auditor / reviewer | Both | Reads the corpus and must determine what was in force at a given date | Cannot establish what the organisation actually believed and when |

The current workflow in both domains is: **nobody checks.** Contradictions are discovered when someone acts on the wrong record, not before. This is measurable — in Domain A a superseded PEP still returns as a topically relevant match for its own subject; in Domain B a corrected record leaves its downstream descendants untouched.

### 1.5 SDG alignment and its boundary

SDG 9 (Industry, Innovation and Infrastructure) applies: the project targets the reliability of institutional record-keeping in engineering and maintenance organisations. **This alignment is context only. It is not the claimed contribution and it is not part of the CCP argument.**

---

## 2. Solution Landscape and the Evidenced Gap

### 2.1 Structural comparison

| Existing solution | Problem and target users | Core approach | Evidence-based limitation | Implication for Halite |
|---|---|---|---|---|
| ADR tooling (adr-tools, log4brains, adr-manager, ADR Manager VS Code extension) | Developers authoring decision records | File scaffolding, templating, status field editing, static site publishing | Status is a field a human sets by hand. No tool detects that a new record conflicts with an existing one; the "superseded" marker is manual and, in practice, usually absent | The detection step — the part that is actually hard — is entirely unaddressed |
| Retrieval-augmented assistants over document corpora | Anyone querying organisational documents | Chunk, embed, retrieve top-k, generate | Retrieval optimises topical similarity. A superseded record is maximally similar to its own subject, so it ranks *high*. Retrieval has no notion of "still in force" | Halite's contribution sits before retrieval: deciding which records are still valid |
| Version control and diff tooling | Developers | Line-level change history over files | Tracks textual change to a file. Has no representation of a *claim* that spans files or documents, and cannot express "this decision overrides that decision" | Conflict is semantic, not textual; diffs cannot express it |
| Maintenance/CMMS platforms (record capture, work-order history) | Field service organisations | Structured work-order storage, scheduling, asset registries | Store records; do not evaluate whether a new record contradicts the stored history, and do not propagate corrections to derived records | Same detection gap, different domain |
| Closest prior FYP category (RAG chatbot over institutional documents) | Students | Retrieval wrapper over a document set | Guide §15 classifies this as a weak pattern where the central capability is supplied by the external model | Halite must locate its contribution in the pairing, adjudication and propagation logic, not in the model |

### 2.2 The gap, stated precisely

Existing systems either (a) let a human declare supersession manually, or (b) retrieve by topical similarity with no validity model. **No available system detects, adjudicates and propagates conflict between records automatically.** The literature confirms the harder half of this: language models perform acceptably when a constraint is explicit and locally visible, and degrade sharply when the constraint is implicit or must be recovered from separated context.

### 2.3 Validating that the problem is real (guide §B.1)

Stream B requires evidence that the problem exists, matters, and is not already adequately solved. Assertion is not evidence. The following is the required evidence set; items already obtained are marked, items outstanding are named as outstanding rather than implied.

| Evidence required | Status | Detail |
|---|---|---|
| Stakeholder contact | **Outstanding — highest-priority gap** | Target: 5 practising developers or tech leads who maintain a decision record set, and 1 records supervisor at a service organisation. Who was consulted, when, and what was learned must be recorded. Assumed users do not count. |
| The current workflow, described concretely | **Partially obtained** | Current practice in both domains is that no consistency check occurs at all. Records are read as retrieved; contradiction is discovered by acting on the wrong record. To be quantified with stakeholders: how often, and at what cost in rework time. |
| Consequence of failure | **Obtained, documented** | Domain A: implementation against a superseded constraint, causing rework and architectural drift. Domain B: incorrect recorded service history on a physical asset, with warranty and compliance exposure. |
| Why existing products do not serve it | **Obtained** | Structural comparison in §2.1, based on inspection of real tooling rather than feature lists. Note per guide §B.1: "not available here" and "it is expensive" are market observations, not technical gaps — no such claim is made here. The gap claimed is functional: no product performs automatic detection, adjudication or propagation. |
| Constraints that are not negotiable | **Obtained** | Enumerated in §3.1. These are where the computing complexity lives. |

**The stakeholder gap is the single largest weakness in this proposal and is not disguised.** Under Stream B it is the first thing the panel will press. It is addressed as POC 0 in §7 and tracked as R8 in §10.

### 2.4 What is *not* claimed

Claim discipline matters more than claim size. Halite does **not** claim:

- A novel language model, embedding method, or graph database.
- That contradiction detection between two given documents is unsolved. It is not — an LLM can compare two documents adequately.
- Novelty in extraction, chunking, or semantic retrieval. These are commodity and are classified as **support** components in §11.

The claim is narrower and is stated in §4.

---

## 3. Complex Computing Problem (CCP) Justification

### 3.1 Where the complexity comes from (constraints, not features)

Guide §B.2 is explicit that the most common Stream B failure is a good problem with a shallow solution, and that the remedy is to look harder at the constraints rather than to add technology. The constraints below are what make this problem hard; each maps to a source of genuine complexity named in the guide's own table.

| Constraint (non-negotiable) | Why it cannot be engineered away | Guide §B.2 category |
|---|---|---|
| The corpus contains sources that genuinely disagree, and the disagreement is unmarked | This is the problem itself, not a data-quality defect to be cleaned. The records are correct as written; they were written at different times under different assumptions | Data that is messy, scarce or **contested** — "multiple sources that disagree" |
| A wrong automatic adjudication silently corrupts the record and is not self-announcing | Requires validation, calibrated abstention, human oversight on the residual, and a defensible failure mode. The system must be able to decline to decide | **Correctness with real consequences** |
| The corpus is large enough that exhaustive pairwise comparison is infeasible | O(n²) comparison over thousands of claims cannot be run per ingestion within a usable latency budget. Which pairs to examine must be decided structurally | **Scale or timing behaviour** |
| Every automatic action must be reconstructable afterwards | An auditor must be able to establish what was in force at a given date and why the system demoted a record. This forces an immutable adjudication trail and shapes the schema | **Trust, security and privacy** — "a requirement to prove afterwards what the system did and why" |
| Author, reviewer and auditor want incompatible things | The author wants minimal interruption; the reviewer wants a short high-precision queue; the auditor wants every decision surfaced including automatic ones. The confidence threshold cannot satisfy all three | **Conflicting stakeholder requirements** |
| Source records cannot be reformatted or re-authored | The system must consume records as organisations already write them — terse field text, informal transcripts, inconsistent document conventions. Requiring authors to change how they write defeats the purpose | Integration with a system whose behaviour cannot be changed |

**The §B.2 test applied directly:** if connectivity were perfect, the corpus were clean and internally consistent, every author annotated supersession by hand, and a wrong answer had no consequence — would this still be a hard computing problem? **No.** Which confirms that the constraints *are* the project. They are therefore stated, designed for, and evaluated explicitly in §6, not mentioned in passing.

### 3.2 Seoul Accord characteristics

Per Seoul Accord D.4.1 and guide §3. Characteristics claimed with project-specific evidence; characteristics only weakly present are stated as such rather than asserted.

| # | Characteristic | How it applies to Halite |
|---|---|---|
| 1 | **Conflicting requirements** | Detection recall competes directly with false-conflict rate. Flagging aggressively surfaces every real supersession and floods the reviewer with topically-similar-but-compatible pairs; flagging conservatively keeps the queue usable and misses real conflicts. Separately, automation coverage competes with correctness: every pair resolved without a human is a pair where a wrong adjudication silently corrupts the record. The confidence gate (§5.4) is where this trade-off is resolved explicitly rather than hidden. |
| 2 | **No obvious solution / depth of analysis** | The naive solution — compare every record against every other — is quadratic and infeasible at corpus scale. Which candidate pairs are even worth examining is the design problem, and it has no standard answer. |
| 3 | **Depth of knowledge** | Requires graph traversal and pruning strategy, retrieval and embedding behaviour, LLM failure modes and self-consistency estimation, confidence calibration, precision/recall evaluation design, and domain knowledge in two unrelated fields. |
| 4 | **Unfamiliar issues** | Confidence calibration against a labelled set, and multi-hop provenance propagation through generated artefacts, are not routine development activities. |
| 5 | **Beyond standard practice** | No framework, template or standard procedure produces conflict adjudication over a record corpus. Neo4j, FastAPI and a hosted LLM are used, but none of them solves the central problem. |
| 6 | **Diverse stakeholders** | Three roles with incompatible success criteria — the author wants minimal interruption, the reviewer wants a short high-precision queue, the auditor wants every decision traceable including the automatic ones. These conflict directly at the confidence threshold, and they shape the RBAC model and the immutable adjudication trail. Two unlike organisations add a second axis: a tech lead and a records supervisor differ in authority, tolerance for false alarms, and regulatory obligation. **Evidenced by POC 0, not asserted** — the guide notes this is the most commonly over-claimed characteristic, so the claim stands or falls on the recorded consultations. |
| 7 | **Significant consequences** | An incorrect automatic adjudication silently marks a valid record as superseded, or leaves an invalid one in force. In Domain B this affects the recorded service history of a physical asset. This is why the system must be able to abstain (§5.4) rather than always decide. |
| 8 | **Interdependence** | The five pipeline stages are not independent screens. Pruning strategy determines classifier load; classifier output determines adjudication input; adjudication confidence determines propagation depth; propagation results feed back into the review queue. A change in any stage changes the measured behaviour of the others. |
| 9 | **Ill-defined requirements** | "Does record B supersede record A?" is not crisply defined at the outset. Partial supersession is common and real: observed instances include *"supersedes some aspects of ADR-15 and ADR-16"* and *"partially supersedes"*. Reducing this ambiguity to a labelling standard the team can apply consistently is itself project work, and is tested at POC stage (§7). |

**Claimed clearly: 1, 2, 3, 4, 5, 7, 8, 9. Present but limited: 6.**

No complexity is manufactured, and none of it comes from the feature list. Every characteristic above traces to a constraint in §3.1 that the environment imposes and the team cannot remove. The two-domain design is not a complexity claim — it is a product and control decision justified in §6.2 — and the domain toggle, the RBAC roles and the tenant partition are explicitly **not** claimed as difficulty. They are standard engineering, disclosed as such in §5.1 and §5.5, because guide §B.4 names feature accumulation and interface-as-contribution as the two hazards this project is most exposed to.

---

## 4. Contribution Statement

Written in the form required by guide §4:

> **Existing approaches** either require a human to manually declare that one record supersedes another, or retrieve records by topical similarity with no model of whether a record is still in force — **but they remain weak** where the corpus is large enough that a person cannot inspect every pair, where the supersession relationship was never written down, and where derived records have silently inherited content from a record later found to be wrong. **We will contribute** a domain-independent pipeline that automatically identifies candidate conflicting record pairs by graph-constrained pruning, classifies the conflict type, adjudicates the winner from evidence signals rather than from user input, propagates the consequence to downstream dependents, and gates every automatic action behind a calibrated confidence threshold that routes low-confidence cases to a human queue — **through** a Neo4j-backed claim graph with pluggable per-domain extraction adapters, **and evaluate it** against author-recorded supersession ground truth in published RFC corpora, against a harder hand-labelled ADR set, and against asset-linked maintenance records, reporting detection precision/recall, adjudication accuracy, false-conflict rejection rate, propagation precision/recall and automation coverage at fixed precision.

### 4.1 Contribution types claimed

Ordered as a Stream B project should order them — the problem and the workflow first, the method as the means:

- **Problem/requirement contribution** — a formulation of record-set consistency maintenance as a detect-adjudicate-propagate problem with a calibrated abstention path, derived from the constraints in §3.1 rather than from a published task definition. Evidence that the problem is real comes from POC 0, not from assertion.
- **System/architecture contribution** — a deployable multi-tenant system operating under the non-negotiable constraints of §3.1: an immutable adjudication trail for auditability, structural pruning to hold per-ingestion latency inside budget at corpus scale, role-separated review, and defensible behaviour when the external model is unavailable.
- **Human/workflow contribution** — a review workflow that reduces reviewer load by resolving high-confidence cases automatically while routing the residual, with the trade-off exposed as a tunable threshold rather than hidden in a default. Evaluated against the measured current workflow (§6.3), not against interface appearance.
- **Method contribution** — the pruning + classification + evidence-based adjudication + confidence-gated propagation pipeline, measured against the baselines in §6.3.
- **Evaluation contribution** — a labelled conflict benchmark assembled from author-recorded supersession links in both domains, with a documented labelling protocol for the partial-supersession cases.

---

## 5. Proposed System

### 5.1 Design principle: one core, two adapters

The system is **one mechanism with two domain adapters**, not two systems sharing a shell.

```
                    ┌─────────────────────────────────────────┐
                    │        DOMAIN-INDEPENDENT CORE          │
   ┌──────────┐     │  ┌───────────────────────────────────┐  │
   │ Domain A │────▶│  │ 1. Claim normalisation            │  │
   │ adapter  │     │  │ 2. Candidate pairing (graph-      │  │
   │ (SWE)    │     │  │    constrained pruning)           │  │
   └──────────┘     │  │ 3. Conflict classification        │  │
                    │  │ 4. Evidence-based adjudication    │  │
   ┌──────────┐     │  │ 5. Propagation to dependents      │  │
   │ Domain B │────▶│  │ 6. Confidence gate → auto | queue │  │
   │ adapter  │     │  └───────────────────────────────────┘  │
   │ (Maint.) │     │         Shared claim graph (Neo4j)      │
   └──────────┘     └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │  Review queue · Audit trail · API │
                    └───────────────────────────────────┘
```

**Stages 1–6 contain no domain logic.** They operate on normalised claims. The adapters supply only: how to parse the source format, how to identify the subject entity, and how to read a timestamp and a source-authority level.

**The domain toggle is configuration, not contribution.** Selecting a domain at signup or first use chooses which adapter is active and which tenant partition is bound. It involves no algorithmic decision and is explicitly excluded from the CCP claim, per guide §15 ("interface treated as contribution") and §B.4 ("feature accumulation").

### 5.2 Graph schema

The current implementation already declares `Component, Decision, Commit, Ticket, Document` with `SUPERSEDES` and `MAY_INVALIDATE` edges. The revision generalises this into a shared core plus per-domain subtypes.

**Shared core (domain-independent):**

| Node | Purpose |
|---|---|
| `Claim` | An atomic normalised assertion: subject, predicate, object, scope, timestamp, source-authority, status |
| `Source` | The document, record, commit or transcript a claim was extracted from |
| `Subject` | The entity a claim is about — a software component in Domain A, a physical asset in Domain B |
| `Actor` | Author or approver, used for authority weighting and audit |
| `Tenant` | Organisation boundary; every node carries a tenant key |

| Edge | Meaning |
|---|---|
| `ABOUT` | Claim → Subject |
| `EXTRACTED_FROM` | Claim → Source |
| `SUPERSEDES` | Claim → Claim, with `scope` (full / partial) and `confidence` |
| `CONTRADICTS` | Claim → Claim, unresolved |
| `DERIVED_FROM` | Claim → Claim; **the provenance edge that makes propagation possible** |
| `PRECEDED_BY` | Chronological ordering within a Subject |
| `FLAGGED_BY` | Claim → adjudication event, for audit |

**Domain A subtypes:** `Component`, `Decision`, `Commit`, `Ticket` — retained from the existing implementation.
**Domain B subtypes:** `Asset`, `ServiceRecord`, `Technician`.

The core queries operate on `Claim` and `Subject`. Domain subtypes inherit from them and carry no separate traversal logic.

### 5.3 Pipeline stages

**Stage 1 — Claim normalisation.** Each source is parsed into atomic claims with a normalised subject/predicate/object structure, a timestamp, and a source-authority tier. Two claims cannot be compared unless they are in comparable form; this stage exists to make comparison possible, not to be clever.

**Stage 2 — Candidate pairing.** Exhaustive pairwise comparison is O(n²) and infeasible. Candidates are pruned to claims that share a subject entity, or that lie within *k* hops in the graph. **This is where the graph is load-bearing.** Without structural pruning the classifier cannot be run at corpus scale; the graph is not a storage choice, it is the tractability mechanism. This must be stated explicitly at defense.

**Stage 3 — Conflict classification.** Each candidate pair is classified into:
- No conflict
- **Scope-disjoint false conflict** — appears contradictory, applies to different scopes. Expected to be the majority class and the dominant error source.
- Direct contradiction
- Supersession (full or partial)
- Implementation drift (Domain A) / record correction (Domain B)

**Stage 4 — Evidence-based adjudication.** No user input. The winner is computed from:

| Signal | Rationale |
|---|---|
| Recency | Later claims generally supersede earlier ones |
| Source authority | Merged code > formal decision record > meeting transcript > chat (Domain A); approved corrected record > technician-submitted record (Domain B) |
| Explicit supersession language | Direct textual evidence when present |
| Corroboration count | Independent sources agreeing |
| Enforcement evidence | Does the current system state actually reflect the claim |

Signals are combined into a score with a confidence value.

**Stage 5 — Propagation.** When a claim is demoted, the graph is traversed along `DERIVED_FROM` to mark dependent claims `provisional`. Multi-hop, and unreachable without traversal. This is the component that no comparable system implements.

**Stage 6 — Confidence gate.** Above threshold → applied automatically, logged to the audit trail. Below threshold → written to the review queue, ranked by expected impact.

### 5.4 On "fully automatic"

The system is **fully automatic in detection and adjudication, with a calibrated abstention path.** It requires no human curation: nobody writes rules, tags records, or maintains the graph. It does not claim that every conflict is resolved without a human, because a silently wrong adjudication corrupts the record irreversibly.

The reportable result is therefore not "no humans" but **automation coverage at fixed precision** — the fraction of conflicts resolved automatically while holding adjudication precision at a stated level. Framing it this way pre-empts the panel's first question and turns a limitation into a measured quantity.

### 5.5 RBAC and multi-tenancy

Three roles, modelled in the graph (no second database):

| Role | Capability |
|---|---|
| Contributor | Submit sources; view claims for their tenant; no adjudication override |
| Reviewer | All contributor rights, plus accept/edit/reject on the review queue |
| Administrator | Tenant configuration, domain adapter selection, user and role management |

Tenant isolation is enforced by a mandatory tenant key on every node and a route-level guard on every query path. **This is standard engineering practice and is claimed as a support component, not a contribution.** It is included because §1.2 of the guide requires a deployable system with deliberate configuration and credentials handling — not because it demonstrates complexity.

### 5.6 Planned extension — mined diagnostic dependencies and the query interface

This is **not** proposal-defense committed scope. It is stated here because it is what the committed core produces at scale, and because it is where the graph stops being storage and starts being reasoning.

**The observation.** A correction does not only tell you that an earlier record was wrong. It tells you *what it was wrong about*. In one real pair on tail 6704Z, the first record attributed a slide-light fault to girt bar lubrication; the second, filed the same day, found debris on a proximity sensor. The symptom presented at one component; the cause lived in another.

**The mechanism.** Every supersession the conflict engine detects where the superseded and superseding records name **different components or JASC systems** is one observation of a misdiagnosis relationship. Aggregated across the corpus, these become weighted `MISDIAGNOSED_AS` edges between components — mined as a by-product of the committed pipeline, not built separately.

Edge weight is **lift**, not raw frequency: how much more often two components co-occur in a correction than their independent base rates predict. Raw counts would rank common parts highest regardless of relationship. Every edge carries its support count, and edges below a minimum support are not surfaced.

**Why this matters to the CCP claim.** The committed core justifies the graph through candidate pruning — real, but narrow. This extension requires genuine multi-hop traversal: symptom → components historically implicated → assets that exhibited it → how it was resolved. That path cannot be produced by a filtered table scan.

**The query interface.** A technician states an asset and a symptom. The system answers from that asset's own history, the fleet-wide misdiagnosis graph, and prior resolutions of the same symptom on comparable assets — returning a *ranked* inspection order rather than the flat protocol order, and surfacing rare prior occurrences that an inexperienced technician would not know to look for. The language model phrases the answer; the ranking comes from mined structure the model has never seen. **This distinction is the defense against "you have built a chatbot."**

**Gating condition.** This extension is only built if a measurement supports it: the proportion of ground-truth supersession pairs in which the superseding record names a **different** `PartName` or `JASCCode` from the record it supersedes. If that proportion is high, misdiagnosis edges exist to be mined. If it is near zero, corrections in this corpus are clarifications rather than re-diagnoses, the extension has no foundation, and it is dropped — recorded as a scope decision under guide §5.3. **The measurement is run before any implementation, and its result is reported either way.**

**Explicitly excluded: parts-demand forecasting.** SDR records are reportable *defects*, not parts-consumption records; routine scheduled replacements never appear. Any annual demand figure derived from them would be biased by reporting requirements while appearing authoritative. It is also a time-series problem rather than a graph-reasoning one, and defining contract terms would require a stakeholder the project does not yet have. Noted as future work; not claimed, not built, not evaluated.

---

## 6. Data and Evaluation

### 6.1 Corpora — verified availability

Feasibility checks have already been run against real sources. Findings, including negative ones:

**Domain A — primary, verified.**

- **Python PEPs.** 568 PEPs carry machine-readable headers. Status distribution: 271 Final, 99 Rejected, 59 Withdrawn, 30 Deferred, 26 Active, **24 Superseded**. **26 carry an explicit `Superseded-By` header** naming a specific PEP, and **23 carry the reverse `Replaces` header**. Bidirectional, author-recorded, machine-parseable, requiring no annotation by the team. This is the primary ground-truth set.
- **ADR corpora.** Five public repositories with genuine ADR directories were located and every file read: 111 ADR files total, of which 12 mention supersession and approximately 8 are real populated links. Observed forms include full supersession with a link, *"supersedes some aspects of"* two separate ADRs, *"partially supersedes"* a named file, and supersession of a GitHub issue rather than an ADR. **This is a small, messy, harder secondary set — appropriate as a degradation test, not as a primary corpus.** Its small size is stated openly rather than hidden.

**Domain B — secondary, verified with one open item.**

- **MaintNet aviation dataset: ruled out.** Downloaded and inspected. 6,169 records, five columns (ID, problem, action, combined text, edit code). **No asset identifier and no date.** Mean record length 13.5 words, median 13, 64% under 15 words. Without an asset key and a timestamp, per-asset history and chronological chaining are impossible, and a 13-word record cannot be meaningfully degraded to simulate a fragmentary report. **This finding invalidated the earlier maintenance-domain plan and forced the change of corpus. It is reported as a finding, per guide §12.**
- **FAA Service Difficulty Reports: adopted.** Public CSV downloads by year, roughly 1.7M records from 1975. Fields confirmed by direct inspection of the 2025 file: `DifficultyDate`, `RegistryNNumber` (tail number = physical asset identity), aircraft make/model/serial, `PartName`, `PartCondition`, `PartLocation`, `JASCCode`, and a free-text `Discrepancy` field typically 40–150 words. Repeat tail numbers are present within days (one airframe carried nine records across three days on the same defect area). Critically, **records naturally reference earlier records** — one observed entry reads "SUPPLEMENTAL REPORT FOR (…)" citing a specific earlier report ID, and others read "SEE LONG HISTORY" or "CHECK HISTORY". These are naturally occurring assumed-context records and author-recorded links, which removes the "you manufactured the gap you then measured" objection.

> **Open item, to be closed before proposal defense:** full-year download and computation of (a) tail-number fill rate, (b) records-per-tail distribution after deduplication, (c) count of explicit supplemental-report references. Near-duplicate filings are common and must be deduplicated or the history depth will be overstated. If records-per-tail after deduplication is too thin to support propagation chains, Domain B is reduced to an extraction-and-detection demonstration and the propagation evaluation runs on Domain A only — recorded as a scope decision under guide §5.3.

### 6.2 Why two domains, stated as a Stream B project must state it

Two reasons, and they are different in kind.

**Product reason (why the panel is told there are two).** The system is intended for organisations that keep a record set and cannot tell which records are still in force. That description is not specific to one industry. Serving two structurally unlike organisations from one core — a software team and a service organisation — is what makes the claim *"a system for record-keeping organisations"* rather than *"a system for one team we happened to talk to."* It is also what produces genuinely diverse stakeholders (characteristic 6): a tech lead and a records supervisor have different authority, different tolerance for false alarms, and different audit obligations, and the design must satisfy both without quietly favouring one.

**Engineering reason (why it is a control, not scope inflation).** A single-domain result cannot distinguish "this mechanism works" from "this mechanism is fitted to this corpus." The domains are deliberately unlike — Domain A has long, formally structured documents with explicit status fields; Domain B has short, jargon-dense field text with implicit references. If the same core holds up on both with only the adapter changed, domain-independence is evidenced rather than asserted.

**Effort allocation: approximately 60% Domain A, 40% Domain B.** The split is driven by ground-truth availability, not by importance. Domain A carries the bulk of the quantitative evaluation because author-recorded supersession links exist there in volume; Domain B carries the harder real-input test, the stronger consequence argument, and a second stakeholder organisation.

**Committed scope covers one domain end to end.** Per §8.1, the committed core is Domain A complete through the full pipeline plus Domain B ingestion, detection and adjudication. If POC 4 (§7) shows the Domain B corpus cannot support propagation chains, Domain B is reduced to detection-only and this is recorded as a scope decision under guide §5.3 rather than quietly dropped. **Two domains never means two half-built systems; it means one core proven twice, at different depths, with the difference stated.**

### 6.3 Baselines

Every metric is reported against a stated baseline, per guide §13:

| Evaluation | Baseline |
|---|---|
| Candidate pairing | Embedding similarity alone, with no graph constraint. If similarity alone pairs as well, the pruning stage adds nothing and this must be reported. |
| Conflict classification | Direct LLM prompt over the pair with no pipeline |
| Adjudication | Recency-only heuristic (always favour the later record) |
| Propagation | No propagation (current practice: nothing happens) |
| Retrieval quality | Keyword matching, as currently implemented |
| **Reviewer workload and accuracy** | **The measured current manual workflow.** Guide §B.3 names the missing measured baseline as the most common Stream B omission, so it is measured rather than assumed: during POC 0, participants are timed on a set task — given a subject and a record set, determine which records are still in force — recording time taken and error rate against known ground truth. This yields the human baseline the system's automation coverage and precision are compared against. Without it, no improvement claim can be made at all. |

### 6.4 Metrics

| Metric | Definition |
|---|---|
| Detection precision / recall | Against author-recorded `Superseded-By` / `Replaces` links, with headers stripped from the input |
| Adjudication accuracy | Given a true conflicting pair, is the correct winner identified |
| False-conflict rejection rate | On topically similar but compatible pairs — **expected to be the weakest number, and reported regardless** |
| Propagation precision / recall | Inject a correction; count correctly and incorrectly flagged dependents |
| Automation coverage at fixed precision | Fraction resolved without human review at a stated precision level |
| Extraction precision / recall | Claim normalisation quality, per domain |

### 6.5 Non-functional requirements (measurable, per guide §6)

| NFR | Target |
|---|---|
| Conflict evaluation latency | ≤ 5s per newly ingested source at p95, corpus of 10k claims |
| Non-generation API latency | ≤ 500ms at p95 |
| Concurrent load | 20 concurrent users on ingestion + review queue without error-rate degradation |
| Backend unit-test coverage | ≥ 80% on core pipeline modules |
| Tenant isolation | Zero cross-tenant reads under an adversarial test suite |
| External dependency failure | LLM/API failures queue for retry rather than drop; degraded mode documented and demonstrated |

### 6.6 User acceptance

Per guide §13.1, UAT is required and planned from proposal stage. Participants: Domain A — 5–8 practising developers on a real repository decision set. Domain B — a records supervisor at a local service organisation if secured; otherwise a **declared proxy**, with the substitution stated now rather than at final defense, and with an explicit statement of what a proxy result can and cannot support.

---

## 7. Proposal-Stage POC (mandatory — to be demonstrated, not described)

Per guide §12, the POC tests the assumption carrying the greatest risk. Guide §12 also states that where the highest risk is genuinely non-technical — access, permissions, data availability — the evidence must address *that* risk, in the same disciplined form.

**As a Stream B project, the greatest risk is tested first: that the problem is real to the people who face it and that the records can be obtained.** The method risks follow immediately, because a Stream B project that cannot locate a complex computing problem fails at defense regardless of how real the problem is.

### POC 0 — The problem is real, and stated by people who face it *(Stream B primary risk)*

**Risky assumption:** that practitioners actually act on superseded records, and that this costs them something. If they say they always know which record is current, the problem does not exist and the project should be reconsidered.

**Setup:** structured conversations with 5 developers or tech leads who maintain a decision record set, and 1 records supervisor at a service organisation. One question drives it: *what did you get wrong because you were working from something that had changed, and what was the change?* Record who was consulted, when, and what was learned.

**Evidence to present:** the recorded consultations, plus at least three concrete instances the panel can examine, plus a statement of what changed in the requirements as a result of the conversations — per guide §B.4, "assumed users" is a named hazard.

**What changes on failure:** if practitioners report they have no such problem, the Domain A framing is withdrawn and the project narrows to Domain B, where consequence is stronger and the record is formal.

### POC 1 — Detection is possible from text alone

**Risky assumption:** that supersession is inferable from the body text, rather than only ever stated in a status header. If it is only in the header, the evaluation is circular and the project has no basis.

**Setup:** 10 PEP pairs with a known `Superseded-By` relationship. Headers stripped. Pipeline run on body text only.

**Result to report:** how many of the 10 were recovered, and — for those missed — whether the supersession was genuinely unstated in the body.

**What changes on failure:** if recovery is near zero, the detection claim is withdrawn and the project re-scopes to adjudication and propagation over *declared* conflicts only.

### POC 2 — Conflict is labellable consistently

**Risky assumption:** that "does B conflict with A" is well-defined enough for evaluation. Partial supersession is common, and if team members disagree on half the cases, no evaluation is possible.

**Setup:** 20 candidate pairs. Two team members label independently, blind to each other. Agreement computed.

**Result to report:** inter-annotator agreement, plus the labelling protocol developed to handle the partial-supersession cases.

**What changes on failure:** low agreement forces a narrowed definition (full supersession only) before approval, not after.

### POC 3 — Propagation depth is non-trivial

**Risky assumption:** that derived claims actually accumulate in chains. If a correction affects only one or two dependents, propagation is a feature, not a contribution.

**Setup:** ingest a corpus, run generation forward chronologically, measure how often a generated claim is used as context for a later one, and the resulting mean chain depth.

**What changes on failure:** if mean depth is near 1, propagation is demoted from core contribution to an optional extension and the contribution statement is rewritten before defense.

### POC 4 — Domain B corpus viability

Per §6.1 open item. Tail-number fill rate, deduplicated records-per-tail distribution, supplemental-reference count.

**All five POCs answer the five questions required by guide §12: what was assumed, what was run, what result was obtained, what was learned or disproved, and what changes as a result.** POC 0 addresses the Stream B access-and-reality risk; POCs 1–4 address the technical risks that determine whether a complex computing problem is present.

---

## 8. Scope

### 8.1 Committed core

| Stage | Committed deliverable |
|---|---|
| Proposal defense | Generalised `Claim`-based schema live; Domain A adapter ingesting PEP/ADR corpora; POCs 1–4 executed with results; conflict detection running end to end on a sample |
| FYP-1 Mid | Candidate pairing with graph pruning; conflict classification across all five classes; Domain B adapter ingesting FAA SDR records; RBAC and tenant isolation scaffolded; SRS submitted |
| FYP-1 Final | Evidence-based adjudication live; confidence gate with threshold set from measured calibration; review queue UI, role-restricted; propagation along `DERIVED_FROM`; working core system end to end in both domains; first deployment attempted; SDS submitted |
| FYP-2 Mid | Full evaluation harness; all metrics running against baselines; NFRs measured; PyTest suite ≥80%; load testing; system test report with defect list by severity |
| FYP-2 Final | Evaluation numbers finalised; UAT completed in both domains; deployed and installable by an outsider from the README; handover package; complete report set |

### 8.2 Optional extensions (explicitly separated, not absorbed)

- MCP server exposing the claim graph to IDE agents
- Multi-repository / multi-site linking
- OCR path for scanned maintenance records
- Per-author phrasing models
- Mined `MISDIAGNOSED_AS` dependency edges and the graph-grounded query interface (§5.6) — **gated on the measurement stated there**, and the highest-priority extension of the set because it is what converts the graph from a retrieval index into a reasoning substrate

These are recorded as extensions. **None of them is permitted to place the committed core at risk.**

### 8.3 What was cut, and why

Per guide §5.3, changes are recorded rather than made silently:

- **Token-efficiency and context-injection framing: removed.** It is an optimisation argument, not a contribution argument, and was correctly rejected.
- **MaintNet/MaintNorm as Domain B corpus: removed.** Disproved by direct inspection (§6.1). Replaced by FAA SDR.
- **Deliberate degradation of real records to simulate fragmentary input: removed.** Constructing the degradation means constructing the effect being measured. Replaced by naturally fragmentary records.
- **Multi-domain as two separate products: not adopted.** Framed as one mechanism, two adapters, for the reasons in §5.1.

---

## 9. Team Ownership

Per guide §5, each member must own a technically meaningful area whose removal would leave a visible gap.

| Member | Primary technical ownership | Shared |
|---|---|---|
| Shahmeer Atif | Pipeline stages 4–6: evidence-based adjudication, confidence calibration, propagation traversal, review queue integration | Architecture, integration, QA, repository discipline, final defense |
| Muhammad Umar | Pipeline stages 1–3: claim normalisation, graph-constrained candidate pairing, conflict classification, graph schema | As above |
| Muhammad Usman Al Haq | Domain adapters (both), corpus acquisition and labelling protocol, evaluation harness, RBAC/tenancy, deployment | As above |

**Removal test:** removing any one member removes an entire pipeline half, the evaluation basis, or the deployment and second domain. No member owns only UI or documentation.

Ownership is interdependent by construction: pairing output is adjudication input, adapter output is normalisation input, and all three meet in the shared evaluation harness.

---

## 10. Risks (initial RAID)

| # | Risk | Impact | Mitigation | Trigger for change |
|---|---|---|---|---|
| R1 | Supersession not inferable from body text | Fatal to detection claim | POC 1 before defense | Re-scope to declared conflicts only |
| R2 | Inter-annotator agreement too low | No valid evaluation | POC 2 before defense | Narrow definition to full supersession |
| R3 | Propagation chains too shallow | Core contribution weakened | POC 3 before defense | Demote propagation to extension |
| R4 | Domain B corpus too thin after deduplication | Second domain unusable | POC 4 before defense | Domain B becomes detection-only demo |
| R5 | False-conflict rate unacceptably high | Review queue unusable | Measured explicitly; scope-awareness added to classifier | Report as a limitation with failure analysis |
| R6 | Panel reads two domains as feature accumulation | Defense risk | §5.1 framing stated up front; toggle explicitly disclaimed as contribution | — |
| R7 | Corpora are clean/formal; real records are messy | Generalisation over-claimed | Domain B is the messy control; degradation reported openly | State the limit rather than defend it |
| R8 | **No confirmed stakeholder in either domain** — the highest-severity risk under Stream B | Fails guide §B.1; panel presses this first; weakens characteristic 6 and invalidates UAT | POC 0 before defense; approach local service organisations and practising developers; declare proxy formally now if not secured | If no stakeholder secured, proxy substitution declared at proposal stage per §6.6 — never at final defense |
| R9 | LLM API rate limits / cost | Pipeline stalls | Retry queue, batching, caching; degraded mode demonstrated | — |
| R10 | Dataset licence terms | Legal/compliance | FAA data is US public domain; PEP and ADR licences to be recorded in the dependency register | — |

---

## 11. External Component Classification

Per guide §14. Every important dependency classified before approval rather than discovered at defense.

| Component | Category | Justification |
|---|---|---|
| Neo4j | **Support** | Storage and traversal engine. The pruning strategy is ours; the database executes it. Replaceable by another graph store without affecting the contribution. |
| FastAPI, React, Docker, Vercel | **Support** | Infrastructure and interface. |
| Embedding model | **Support** | Similarity scoring. Used as one input to pairing, not as the pairing decision. |
| Groq / Gemini hosted LLM | **Core-assist** | Contributes to classification and claim normalisation. Justified: no local model is runnable within team resources at required quality. Limitations stated, outputs validated against labelled sets, fallback path defined, surrounding design explainable and modifiable. **The contribution remains identifiable independently: the model classifies a pair we selected, using signals we computed, gated by a threshold we calibrated.** |
| — | **Core-replacement** | **None.** No component supplies the pairing strategy, the adjudication signal combination, the confidence calibration, or the propagation traversal. |

**The §14 test applied directly:** if the hosted LLM were swapped for a comparable alternative, the contribution survives — pairing, adjudication signals, calibration and propagation are unchanged. If Neo4j were swapped, the contribution survives. The contribution does not sit in any external component.

---

## 12. AI-Assisted Development Disclosure

Development is conducted at Level 2 (AI-assisted), per guide §8. An AI usage log is maintained alongside the dependency disclosure sheet and updated as work proceeds. For every CCP-relevant component — pairing, classification, adjudication, calibration, propagation — the log records how output was verified before being relied on, and the owning member is able to explain the component, justify it against a rejected alternative, predict what breaks, and modify it under questioning.

---

## 13. Open Items Before Defense

Stated plainly rather than concealed:

1. **POCs 1–4 not yet executed.** All four are required before the proposal is defensible.
2. **Domain B corpus statistics not yet computed** (§6.1 open item).
3. **No confirmed Domain B stakeholder.** Either secure one or formally declare the proxy now.
4. **Labelling protocol for partial supersession not yet written.** Output of POC 2.
5. **Confirm with supervisor** that "merge both" means one mechanism evaluated across two domains (this document's reading), and not two independent systems behind a shared login. The two readings produce materially different projects and different effort budgets.

---

## 14. One-Sentence Vagueness Test

Per guide §6, completed for the hardest part of the project:

> **The system shall** identify, without human input, which previously recorded claims are contradicted or superseded by a newly ingested record, adjudicate which claim remains in force, and mark every downstream claim derived from a demoted one as provisional — **for** a reviewer responsible for the integrity of an organisation's record set — **and we will know it works when** it recovers author-recorded supersession links from body text with the headers stripped, at a measured precision and recall against a stated baseline, while resolving a reported fraction of cases automatically at a fixed precision level and correctly abstaining on the remainder.
