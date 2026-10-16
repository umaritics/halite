# Halite — Proposal Defense Speaking Script

Paired with `Halite_Pitch_Slides.md`. ~9 minutes of talking, timed per slide. Say this, don't read it — but every number here is verified against `docs/evaluation_results.md` and `docs/misdiagnosis_density.md`, so you can say it exactly.

One rule for the room: if you're asked a number that isn't in this script or in `Halite_Defense_Package.md` Part 1, say "I don't have that measured, I'll get back to you" — don't estimate live.

---

### Slide 1 — Title (30s)

> "Good [morning/afternoon]. I'm presenting Halite, on behalf of myself, Muhammad Umar, and Muhammad Usman Al Haq, supervised by Syed Muhammad Saad Salman. We're declaring Stream B — this idea started from an observed workflow failure in maintenance record-keeping, not from a paper. One sentence: maintenance organisations file corrective records that silently contradict earlier records on the same physical asset, and nothing today catches it automatically."

---

### Slide 2 — Problem and users (75s)

> "Here's a real example from our corpus, not a constructed one. Tail number 6704Z. Same aircraft, same day. First technician: slide light won't extinguish, lubricated the girt bar. Second technician, same day, same fault description — but this one writes 'check history,' investigates further, and finds the real cause: debris on a proximity sensor. The first fix was wrong. Nothing in the FAA's file connects these two records — they sit roughly two hundred rows apart. The only link is one technician telling another human being to go look.
>
> That's the workflow today, for three groups. The field technician writes a terse record assuming the reader already knows the asset's history. The records supervisor manually reconciles a new record against paper or PDF history only when something looks off — which means most of the time, nobody's reconciling anything. And an auditor trying to reconstruct what the organisation actually knew at a given date has no way to do it. The current workflow, stated plainly, is: nobody checks. The contradiction surfaces only after someone has already acted on the wrong record."

---

### Slide 3 — Existing solutions (60s)

> "We looked at what already exists before assuming a gap. CMMS platforms — work-order software — store records and schedule maintenance, but never evaluate whether a new record contradicts stored history. Retrieval-augmented assistants over documents rank by topical similarity, which is actually the wrong property here — a superseded record is maximally similar to its own subject, so it ranks high, not low. It has no notion of 'still in force.' And the manual instruction we saw on the last slide — 'check history' — doesn't scale. One airframe in our corpus alone carries a hundred and fifty-three records.
>
> We also checked the closest prior-FYP pattern directly against our own FYP guide, which names 'generic chatbot or retrieval wrapper' as an explicitly weak pattern. We take that seriously — our contribution has to sit in the detection and adjudication logic, not in the language model, and I'll show exactly where that boundary is on slide six."

---

### Slide 4 — R&D and technical basis (50s)

> "Two research decisions we made with evidence, not assumption. We initially planned to use the MaintNet aviation dataset for the maintenance domain. We downloaded and inspected it directly: no asset identifier, no date field, average record length under fourteen words. You cannot build a per-asset history or a chronological chain without an asset ID and a date, so we dropped it and adopted FAA Service Difficulty Reports instead — public domain, confirmed tail numbers, confirmed dates, and records that naturally self-reference each other in the text.
>
> Technically, we grounded two decisions in published work: our classifier runs five-pass self-consistency majority voting, following Wang et al. 2022 on self-consistency in language model reasoning, rather than trusting a single LLM call. And our decision to prune candidates through the graph rather than a filtered SQL query is grounded in published benchmarking on graph versus relational performance for multi-hop traversal."

---

### Slide 5 — Complex computing challenge (70s)

> "Here's the test we hold ourselves to, straight from our own FYP guide: if the corpus were clean, every technician annotated supersession by hand, and being wrong cost nothing — would this still be a hard computing problem? No. Which means the complexity has to come from the constraints, not from the feature list, and that's how we're presenting it.
>
> Concretely: automation coverage directly competes with correctness, and that trade-off is coded, not just discussed — a 'contradicts' or 'partial supersedes' classification never auto-applies at any confidence level, by design. The domain knowledge required spans aviation part taxonomies, source-authority hierarchies, and confidence calibration under uncertainty. The consequences are real — a wrong automatic decision silently corrupts a regulator-facing aviation record. And the five pipeline stages are genuinely interdependent: what the pruning stage returns determines what the classifier sees, which determines the adjudication input, which determines whether we act automatically or ask a human.
>
> I'll say plainly where we're weaker: we don't yet have a confirmed records-supervisor stakeholder, so the 'diverse stakeholders' characteristic is asserted less strongly than the others — we're treating that honestly rather than overclaiming it."

---

### Slide 6 — Proposed solution and contribution (60s)

> "The pipeline: ingest a record, prune candidates using the asset graph, classify the conflict type with a five-pass majority vote, adjudicate the winner from evidence signals — recency, source authority, explicit citation language, part agreement — not from any user input, then gate the decision behind a calibrated confidence threshold. Above threshold, it applies automatically and logs the action. Below threshold, it goes to a human review queue.
>
> One architecture note worth stating explicitly: this same pipeline already runs a second domain — software decision records — in our shipped codebase, with only the domain adapter swapped. I'm not presenting that evaluation tonight, but it's evidence the mechanism isn't fitted specifically to FAA text.
>
> On external components: Neo4j is support — replaceable without touching the contribution. The Groq-hosted LLM is core-assist — justified because no locally-run model meets the quality bar within our resources, its outputs are validated, and there's a defined fallback when it's unavailable. Nothing in this system is core-replacement; if you swapped the model, the pruning strategy, the adjudication signals, and the calibration would all still be ours."

---

### Slide 7 — POC (mandatory — live, ~90s)

> "This is not a description, I'll show it running. [Switch to the live app.] I'm submitting a real record on tail eight-one-three S-K. Watch the pruning line — it reads 'examined twenty-five of one hundred fifty-three records on this asset.' That's the graph doing its job: this asset alone would need over eleven thousand pairwise comparisons without it. Now the classification comes back with a label and a rationale, a confidence score, and a routing decision — either it auto-applies and writes directly to the graph, or it lands in the review queue for a human.
>
> I also want to show you a measurement we ran and it failed — on purpose, before we saw the result. We pre-registered two thresholds for whether component-level misdiagnosis patterns were worth mining as a feature: at least thirty percent of corrections naming a different part, and at least ten distinct component-pair patterns with real support. We hit sixty-five point two percent on the first test — but only one pair cleared the support bar on the second. So we dropped that extension and recorded why, rather than quietly building it anyway. That sixty-five point two percent number is the single fact our whole CCP claim rests on, and it's real, measured, on a hundred and forty-one author-recorded pairs, not asserted.
>
> Right now, live, this system holds two thousand and seventy-nine real FAA records and has detected a hundred and twenty-one conflicts against the actual Neo4j graph behind me."

---

### Slide 8 — Evaluation plan and risks (75s)

> "On a hundred and forty-one ground-truth pairs plus two hundred nine sampled negatives, our engine achieves seventy-nine percent precision and sixty-six percent recall at pair level. The obvious baseline — always assume the most recent prior record supersedes — gets higher raw recall, ninety-one percent, but its false-conflict rate is one hundred percent: on every single one of the two hundred nine negative pairs, it claimed a supersession that doesn't exist. It cannot abstain. Ours is wrong on four point eight percent of negatives instead of a hundred. In a system that writes to real maintenance records, that's the property that matters.
>
> We also swept the confidence threshold from zero point one to zero point nine. Performance is flat — F1 between roughly zero point seventy-six and zero point seventy-six two — across the lower half of that range, and collapses above zero point six. So our threshold choice isn't a knife-edge pick, but proper calibration on a held-out split, not the full set we tuned on, is committed work for FYP-1, and I want to be upfront about that rather than have it discovered in questions.
>
> Our top risk right now, honestly: recall at zero point sixty-six leaves real supersessions un-flagged, and we've actually found the specific reason while auditing our own code this week — the pipeline currently only classifies the single top-ranked candidate out of up to twenty-five, even though all twenty-five are scored. Extending classification to the top few candidates is our named fix, not a hidden problem. Second risk: we don't have a confirmed records-supervisor stakeholder yet — we're pursuing that now and will declare a proxy explicitly if we don't secure one, rather than let it surface for the first time at final defense."

---

### Slide 9 — Work division and iteration plan (40s)

> "Ownership splits along the pipeline itself, not by feature. I own evidence-based adjudication, confidence calibration and the review queue. Umar owns candidate pairing, classification, and the graph schema. Usman owns the domain adapter, corpus acquisition and labelling, the evaluation harness, and deployment. If you removed any one of us, an entire pipeline stage or the evaluation basis disappears — nobody here owns only slides or UI.
>
> For FYP-1, our committed deliverable is the recalibrated confidence gate on a genuinely held-out split, with a measured recall improvement over today's sixty-six percent, plus the requirements and design baseline. FYP-2 adds the full evaluation harness against every baseline, non-functional targets measured rather than asserted, and stakeholder acceptance testing."

---

### Slide 10 — DEI, ethics and legal (35s)

> "Briefly: this system evaluates records, not people — no technician is scored or individually flagged, and the review interface targets full keyboard and screen-reader accessibility. On ethics — the FAA data we use is public domain and contains no personal information. More importantly, the system never silently edits a record. Every automatic action is logged and reversible, and anything ambiguous is routed to a human rather than resolved on its own — that's a deliberate design choice against automation bias in a safety-relevant record system, not something we added afterward. On compliance — our LLM usage follows Groq's published terms, and our AI-assisted development is logged and disclosed at the level our guide requires, maintained as we go rather than reconstructed for tonight."

---

## Timing summary

| Slide | Target time |
|---|---|
| 1. Title | 0:30 |
| 2. Problem and users | 1:15 |
| 3. Existing solutions | 1:00 |
| 4. R&D and technical basis | 0:50 |
| 5. Complex computing challenge | 1:10 |
| 6. Proposed solution | 1:00 |
| 7. POC (live) | 1:30 |
| 8. Evaluation and risks | 1:15 |
| 9. Work division | 0:40 |
| 10. DEI/ethics/legal | 0:35 |
| **Total** | **~9:45** |

If you're cut to 7 minutes: compress 3 and 4 into one breath each, keep 2, 7, and 8 at full length — those are the ones the panel actually probes.

## If asked why the software domain isn't the headline

> "It exists and runs on the same core — but the maintenance domain has the larger, more rigorously measured corpus and the stronger consequence argument, so that's what we're standing behind tonight. We're not hiding the other domain; we're not overclaiming it either."

Don't volunteer this unless asked — the current pitch is deliberately single-domain to keep the story tight.
