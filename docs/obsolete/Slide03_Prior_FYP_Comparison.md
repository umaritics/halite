# Slide 03 — Prior FYP Comparison (from BS-FYP Repository)

Source: [BS-FYP repository](https://docs.google.com/spreadsheets/u/0/d/e/2PACX-1vTMHFLUiZ3pvejFalloWNbJ_-eiO2uNsEiYb4eN4UjKUzdWQusZgBg3aQ3ylU7fhELcjXpvBgOEPrE4/pubhtml)

Use this to replace the vague “Prior FYP pattern: RAG chatbot over institutional docs” row on Slide 03 of `Halite_Proposal_Defense.pdf`.

---

## What the repository actually shows

### Closest completed priors (with reports)

| Prior FYP | Cohort | What it did | Why it is close | Why it is not Halite |
|---|---|---|---|---|
| **FASTalk (AcademicBot)** | Fall 2019 – Spring 2020 | Generative academic chatbot using university sources (Slate + nu.edu.pk) | Institutional Q&A over campus info | Answers questions; no record supersession |
| **Interactive chatbot for admission inquiries in Roman Urdu** | Fall 2020 – Spring 2021 | Admissions chatbot for student queries | University assistant pattern | Chat only; no conflict / validity layer |
| **GUIDANCE BOT** | Fall 2019 – Spring 2020 | Student-query chatbot (deep learning) | Same “ask the system” pattern | No evolving-record adjudication |
| **WhatNext** | Fall 2019 – Spring 2020 | Career chatbot with a knowledge graph backend | Uses KG + chatbot | KG for guidance, not marking old records untrue |
| **F21-05-R-AutoKG** | Fall 2021 – Spring 2022 | Build RDF knowledge graphs from document collections | Closest “docs → graph” prior | Stops at KG construction/publishing, not conflict detection |

### Closest same-era RAG pattern

Current cohort, proposal-stage — use carefully as “common FYP pattern,” not as finished priors:

- **S25-014-D-CampusHive** — multi-agent RAG chatbot for FAST students/faculty
- **F25-255-D-ExamMate**, **F25-279-D-BlueprintAI**, **F25-301-D-HudaAI** — RAG / RAG+KG document assistants

### Important finding

In the full repository scan, **no prior FYP** does maintenance record-vs-record supersession / conflict adjudication (SDR-style).

Maintenance-adjacent ones (e.g. RATAR remote technician AR, OrangeLine wheel maintenance, Homeease service booking) are different problems.

---

## Paste this into Slide 03

Keep CMMS / Siemens / RAG commercial rows. Replace the prior-FYP row with one of the options below.

### Option A — compact (fits your current table)

| WHAT EXISTS | WHAT IT DOES | WHAT IT CANNOT DO |
|---|---|---|
| Prior FYPs: **FASTalk / AcademicBot**, **Roman-Urdu admissions chatbot**, **AutoKG** | Answer campus/admission queries, or build a document knowledge graph | Never detect when a new filed record proves an older one wrong — no supersession / conflict gate |

**Footer line (keep):**

> A superseded record is maximally similar to its own subject — so retrieval ranks it high, and flags nothing.

### Option B — stronger, 2–3 named prior rows (recommended)

| WHAT EXISTS | WHAT IT DOES | WHAT IT CANNOT DO |
|---|---|---|
| **FASTalk (AcademicBot)** · FAST FYP 2019–20 | University chatbot over campus sources (Slate / nu.edu.pk) | Q&A only — does not mark outdated information as superseded |
| **AutoKG (F21-05)** · FAST FYP 2021–22 | Builds RDF knowledge graphs from document collections | Constructs/publishes a graph — does not adjudicate conflicting records over time |
| Common recent pattern: **CampusHive**-style RAG campus assistants | Retrieve documents + generate answers | Same weak pattern (Guide §15): capability sits in retrieval/model, not validity |

---

## Spoken line for Usman

> “We checked the school’s FYP repository. Closest priors are campus chatbots and document knowledge graphs. They answer or store. None of them detect when a new maintenance record overrides an older one.”

---

## Do not claim

- Generic “prior FYP pattern” with no names
- Siemens / IBM as if they were FYPs (keep them as industry)
- That no RAG FYPs exist (many do)
- That a prior FYP already solved SDR conflict detection (repo evidence does not support that)
