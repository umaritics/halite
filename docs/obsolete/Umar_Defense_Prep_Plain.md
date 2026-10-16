# Umar's Proposal Defense Prep (Plain Language)

For tomorrow. Keep this simple. If you can explain each section out loud without reading, you are ready.

Your slides in the deck: **04 (R&D)**, **05 (CCP / why graph)**, **06 (solution + your stages)**.

---

## 1. The whole project in 60 seconds (memorize this)

Planes (and other machines) get many service reports over time.

Sometimes a later report shows that an earlier report was wrong.

Today, those two reports just sit in a pile. Nothing links them. Nothing marks the old one as outdated. A person has to re-read the whole history by hand.

**Halite's job:** when a new report comes in, find the older reports on the *same plane* that might conflict with it, decide *what kind* of conflict it is, then either:

- mark the old one as overridden automatically (if we are confident), or
- send it to a human to check (if we are not sure).

That is the whole idea. Not a chatbot. Not "store files better." **Find conflicts, decide carefully, do not silently break real records.**

---

## 2. Who does what (so you know your lane)

| Person | In simple words |
|---|---|
| **You (Umar)** | Build the graph shape. Decide *which* old reports are worth comparing. Ask the AI *what type* of conflict it is. |
| **Shahmeer** | After classification: who wins, how sure are we, auto-apply or send to humans. |
| **Usman** | Get data in, adapters, evaluation numbers, deploy. |

Your three stages on the pipeline slide: **1 Normalise · 2 Prune · 3 Classify**.

---

## 3. Data feeding (how records enter) — know this even if Usman owns it

1. FAA CSV files (real public reports).
2. Each row becomes a **ServiceRecord** on an **Asset** (the plane's tail number).
3. We skip rows with no tail number or bad date (we do *not* invent today's date).
4. Records on the same plane get linked in time order (`PRECEDED_BY`).

**You need to say:** "We feed real FAA Service Difficulty Reports. Each report hangs on one aircraft. Without that aircraft link, we cannot do conflict checks."

---

## 4. What YOU own — explain like this

### A) Graph schema (the map)

Think of three sticky notes and three kinds of arrows:

**Nodes (things):**
- **Asset** = one aircraft (tail number)
- **ServiceRecord** = one report
- **Component** = a part named in a report (when we have it)

**Edges (links):**
- **ABOUT** = this report is about this aircraft  
  *(comes almost free from the CSV — tail number column)*
- **PRECEDED_BY** = this report came after that earlier one on the same aircraft  
  *(comes from dates)*
- **SUPERSEDES** = this report overrides that earlier one  
  *(this one is NOT free — our system computes it)*

**One line for the panel:**  
*"Two links come from the file for free. They exist so the third link — supersedes — becomes something we can compute."*

That is exactly what your Slide 6 says. Keep it.

---

### B) Pruning / candidate pairing (your hardest, most important part)

**Problem in one sentence:**  
If we compare every report to every other report, we get about **2.16 million** comparisons. That is too many, too slow, and mostly useless (a report on plane A cannot override a report on plane B).

**What you do instead (3 cuts):**

1. **Same plane only**  
   Follow the ABOUT link. Drop everything on other aircraft.  
   ~2.16M → about **45,764** within-plane pairs.

2. **Score the remaining ones**  
   Give points if they look related:
   - same part name → +3  
   - same system code (JASC) → +2  
   - same location → +1  
   - within 30 days → +1  

3. **Keep at most 25**  
   Cap at `MAINT_MAX_CANDIDATES = 25`.  
   Example: plane **813SK** has 153 reports → full compare would be 11,628 → we keep ≤25.

Also: **77.8% of reports** have no good earlier match at all, so they never go to the AI.

**One line for the panel:**  
*"The graph is not just storage. It is what makes comparison cheap enough to run."*

**If they ask "why not a normal database?"**  
A normal table can store the same rows. The win is the *walk*: "all reports on this plane, then score neighbours." Graphs are built for that kind of walk. We are not claiming graphs are magic — we are claiming this walk is the reason we do not drown in comparisons.

---

### C) Conflict classification (what the AI does for you)

You send the AI **one new report + one old report** (usually the best-scoring prior).

It must pick **one label**:

| Label | Plain meaning |
|---|---|
| `no_conflict` | They do not fight |
| `scope_disjoint` | Look similar, but about different things / scopes |
| `supersedes` | New one replaces old one |
| `partial_supersedes` | New one replaces only part of the old one |
| `contradicts` | They clash, and it is not clear who wins |

You do **not** ask the AI "should we auto-apply?" That is Shahmeer's gate.

You also run the classification **several times** and take the majority answer (self-consistency) so one random AI answer does not decide everything.

**One line for the panel:**  
*"The model only names the conflict type for a pair we already selected. Five of six stages are ours. The model is one stage."*

**Honest weakness you should know:**  
Today we mostly classify the **top-1** scored prior, not all 25. That can miss some real conflicts. Improving recall (finding more true conflicts) is FYP-1 work. Say this calmly if asked — it is maturity, not failure, at proposal stage.

---

## 5. Retrieval vs conflict detection (do not mix these up)

People will confuse "finding similar reports" with "finding conflicts."

| | Retrieval / diagnose | Conflict detection (your work) |
|---|---|---|
| Question | "What should I check for this symptom?" | "Does this new report override an older one?" |
| Output | Ranked helpful history | Labels + later SUPERSEDES links |
| Danger | Showing old wrong answers | Auto-marking the wrong record |

Halite's core claim is the **second** column. Diagnose is useful, but if the panel says "isn't this RAG?", answer:

*"Retrieval finds related text. We decide whether an older record is still true. A wrong old record is often the most similar text — that is why retrieval alone fails."*

---

## 6. How to present YOUR slides (simple script)

### Slide 04 — R&D (you)

Say:
> "We checked if someone already solved record-vs-record conflict in maintenance.  
> Industrial knowledge graphs help diagnosis and organising work — not consistency between reports.  
> The closest aviation system (KEO) uses KG + LLM + RAG, but never talks about conflict, contradiction, or supersede.  
> PaTeCon finds conflicts on structured knowledge graphs with hard rules — free text does not have those rules.  
> Boeing's work on the same FAA data classifies one report at a time, never report against report.  
> So the gap we work on is real: **compare records and mark what is no longer true.**"

Keep research names short. The point is the gap, not the paper titles.

### Slide 05 — Complexity (you)

Say:
> "Brute force is about 2.16 million comparisons.  
> First we stay on one aircraft — big cut, no AI.  
> Then we score by part, system, location, time.  
> Then we cap at 25 candidates.  
> Most records never need the model at all.  
> That is why this is a computing problem, not a UI problem."

### Slide 06 — Solution (you open, then handoff)

Say:
> "Six stages. I own the first three: normalise, prune, classify.  
> Shahmeer owns adjudicate, confidence, and the gate.  
> The model only classifies the pair we chose. It does not decide whether we act.  
> Two graph links come from the file. The third — supersedes — is what we compute."

Then let Shahmeer take adjudication if the team splits speaking.

---

## 7. Questions you will likely get (short answers)

**"Isn't this just an LLM wrapper?"**  
No. We choose which pairs to check. We score them. We cap them. The model only labels one pair. Acting or abstaining is a separate stage.

**"Why a graph?"**  
To cut impossible comparisons down to a small candidate set on the same aircraft. Storage is secondary.

**"What if the AI is wrong?"**  
Wrong labels go to review when confidence is low, or when the label is contradiction / partial. We prefer asking a human over silently corrupting a record.

**"Recall is only 0.66 — isn't that low?"**  
For proposal stage we chose to be careful (few false alarms). Raising recall without flooding false conflicts is the FYP-1 goal.

**"Where is your CCP?"**  
In the constraints: records disagree, wrong auto-decisions hurt, and full pairwise compare does not scale. If every report already marked what it replaced and mistakes cost nothing, this would be easy.

**"What did YOU personally build?"**  
Candidate pairing / pruning, conflict labels, and the graph relationships that make pruning possible.

---

## 8. Slide improvement suggestions (deck is not final)

Your PDF is already strong. Small upgrades only:

1. **Slide 05 title** — "2.16 million comparisons, or 25" is punchy. Keep it. Add one tiny footnote: "POC numbers on current 2,079-record corpus" so they know it is measured, not marketing.
2. **Slide 06** — Add a tiny "not a chatbot" line under contribution: *"Detection and validity, not answer generation."* This blocks the RAG attack early.
3. **Slide 04** — One visual row: "Closest work → still missing: record vs record." Makes the gap obvious in 2 seconds.
4. **Numbers consistency** — Use one set everywhere for pair-level recall/precision. Prefer the live evaluation file your team agrees on tonight; do not mix 0.61/0.80 with 0.66/0.79.
5. **Do not over-pack Slide 08** for proposal — keep targets as *plan*, POC numbers as *evidence so far*. Panels like that honesty at proposal stage.
6. **Umar speaking share** — You should definitely speak Slides 4 and 5 fully, and open Slide 6. That shows ownership without needing deep adjudication jargon.

---

## 9. Tonight checklist for Umar

- [ ] Say the 60-second project pitch out loud twice.
- [ ] Draw Asset / ServiceRecord / ABOUT / PRECEDED_BY / SUPERSEDES on paper from memory.
- [ ] Explain the 2.16M → 45k → 25 cut without looking at the slide.
- [ ] List the 5 conflict labels from memory.
- [ ] Practice the "not a RAG chatbot" answer once.
- [ ] Agree with teammates who says which lines on Slide 6 and 7.

You do not need to sound like a research paper tomorrow. You need to sound like you understand the problem, your three stages, and why the graph cut matters.
