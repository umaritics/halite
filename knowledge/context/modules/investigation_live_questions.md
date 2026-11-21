---
id: mod-investigation-live-questions
title: Managed live questions, durable posteriors and explicit activation
status: active
owners: [Usman]
updated: 2026-11-20
---

# Managed session questions

`SESSION_QUESTIONS_ENABLED=false` is the default. Enabling requires an explicit
`SESSION_POLICY_FILE`, official codebook/schema provenance, matching ranker
version and the 2023 fitted parameters. Invalid enabled configuration fails 503
without saving a turn. The committed policy fixture is **synthetic/experimental**,
not the selected research operating point. No production threshold is installed.

`live_graph.py` creates one read-only knowledge-time snapshot for managed ranking
and likelihoods. Strictly earlier, timezone-aware submission times are required;
missing/invalid/naive dates and equal/future submissions are excluded and counted.
Filtering precedes the ranker's existing limits. Actual ABOUT membership supplies
aircraft history. A known future correction cannot change an earlier visible
record's supersession state. Unknown supersession provenance stays conservatively
historical. Equal-occurrence ties use record ID descending, as in offline replay.

`live_questions.py` builds smoothed matrices from that same snapshot, excludes
referenced records' validated full citation chains from counts, and records the
audit. It applies the deterministic answer/ask/abstain rule to fitted relative
support. Explicit report requests select report mode without a fault decision.
Raw historical ranks/scores remain separate from sorted posterior beliefs.

Every question has a random server-issued ID. The answer body adds `question_id`
to `attribute`/`value`; it must match the current saved question. This closes the
same-attribute stale-tab gap that attribute/value alone cannot detect. Missing or
stale IDs return 409, unoffered values 422. Ownership/open checks happen first.

Answers load the last durable response, reuse its basis, matrices, policy and
codebook, and never read graph records or call the model. Prior/posterior and
answer are saved with the turn. Not-sure preserves beliefs and excludes that
attribute. The three-question budget and answer history survive reload/restart
and new free-text observations; new observations re-rank and condition on earlier
answers rather than silently forgetting them. Inconsistent evidence fails loudly.
The existing conditional turn claim/snapshot transaction prevents double answers,
closure races and partial posterior commits. Replay always returns stored data.

Managed prose is written after the server decision. The model cannot set the
question field or decision. Empty prose/model questions are rejected in favor of
a deterministic explanation; answer turns use `llm_status=not_needed`. Citations
are checked against saved evidence, independently of later graph changes. The
frozen stateless route retains its previous prompt/output/outage behavior; its
internal helper now permits managed sessions to skip legacy prose only.

The UI shows backend options, expected gain, experimental guidance status and
relative support including other. A question identity change resets the selected
option; pending/uncertain writes disable controls. Sentence grounding and accepted
operating-point selection remain separate packages, not falsely claimed here.
