---
id: mod-investigation-grounding
title: Saved sentence audits and independent human calibration
status: active
owners: [Usman]
updated: 2026-11-20
---

# Sentence grounding

`investigation/grounding.py` splits the original prose without rewriting it,
attaches trailing citations (including mixed/numeric-leading FAA IDs), checks L2
against the **saved turn's** evidence IDs and scores each cited source separately.
L3 is content-token containment plus optional cosine similarity, maximized over a
single report; unrelated reports are never unioned to manufacture support.

The fixed stop list retains negation and quantities. Missing named parts,
conditions, quantities, negation mismatch or empty content prevent `supported`.
The part dictionary is fitted solely on 2023 (1,006 names, hash checked on load),
plus names in the exact evidence. These conservative lexical guards are not a
semantic entailment proof: morphology and report-wide negation can cap a valid
sentence, while token overlap can still miss relational errors. Human validation
and the model-judge comparison measure those behaviors; no measured accuracy is
claimed from synthetic tests. The highest-score candidate is authoritative; a
lower-scoring candidate does not override its failed guard.

No configured thresholds means `unrated` for valid citations, with scores kept.
Out-of-turn citations are `unsupported` regardless of thresholds. Uncited sentences
are explicitly `uncited`; only exact case/whitespace-normalized configured safety
templates can be acceptable. The default whitelist is empty.

`SESSION_GROUNDING_FILE` optionally loads explicit experimental/selected settings;
selected settings require label-result and decision references. Invalid settings
fail before inference. Each turn freezes settings before inference, saves the
configuration hash, scores, guards, source narratives and audit with its existing
transaction, and GET replays that stored audit. Structured answers never invoke
an encoder or graph service. An unavailable dense adapter records lexical scores
but withholds blended-calibration ratings; no silent reuse of dense thresholds.

The optional `embed_port.py` imports an existing retrieval encoder if available;
it does not download a model or add a dependency. The current repository has no
real encoder implementation. Dense maths are tested with explicit synthetic
vectors; normal runtime is accurately labelled `lexical`.

Quick diagnosis adds the audit and its full saved narratives under `grounding`;
frozen explanation, ranking and metadata-only `evidence` fields are retained.
Cached prose is audited against the same context-keyed sources/current settings
without another model call. The interface renders original Markdown per sentence,
focusable reasons and citation-source panels; pending/experimental ratings are
explicit. Existing old saved responses continue to render without invented audits.

# Human evaluation protocol

`grounding_packet.py` freezes 150 constructed sentence/report pairs from 50 2024
originals and strictly earlier 2023/2024 negative references, excluding full query
chains. Real text is not represented as generated model output. Source/report
IDs stay disjoint across 99 fit and 51 validation pairs. Blinded browser copies
contain no arms/scores/splits; reviewer labels start empty. User chose **Muhammad
Umar** as Usman's second independent reviewer. No message was sent on his behalf.

`grounding_eval.py` imports two complete fingerprint-bound independent CSVs,
calculates Cohen's kappa, requires explicit adjudication of every disagreement,
selects lexical thresholds on fit-only macro F1 with declared conservative ties,
and reports separate validation precision/recall/confusion counts. Undefined
metrics remain null. Source and method hashes are retained. The proposal stays
unaccepted and whitelist empty until Usman's decision. Human labels, generated
answer validation, L4/no-evidence comparison and 2025 final evaluation remain
outstanding; no synthetic label is used as their substitute.

For model-written quick diagnosis, L2 uses exact bounded prompt sources. The
model-off deterministic template instead receives the full collected evidence
list: its audit uses that supplied/displayed list. This distinction prevents
false out-of-context marks on the template's legitimately listed citations.
