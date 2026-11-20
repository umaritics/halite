---
id: mod-investigation-decisions
title: Beliefs, deterministic decisions and leakage-safe selection
status: active
owners: [Usman]
updated: 2026-11-20
---

# Decision core and experiment boundary

The user explicitly authorized drafting the plan's design note on his behalf.
`docs/fyp1-final/DECISION_LAYER_DESIGN.md` records that AI assistance and precedes
WP-S4 implementation. It does not represent unaided authorship or human labels.

## Pure core

`investigation/beliefs.py` applies stable temperature softmax to at most ten named
scores plus an explicit other bucket, and computes entropy including that bucket.
Without fitted parameters: T=1, other score=minimum named score, calibrated=false.
Empty rankings assign all belief to other. Inputs must be finite and parts unique.
Parameter files require a matching ranker version and a 2023 corpus fingerprint.
Bars remain relative support even after fitting; fitting alone does not authorize
probability wording or claim real diagnostic validity.

`policy.py` implements the specified answer → ask → abstain priority. Numeric
inputs and thresholds are validated, exact boundary equality passes, exhausted
question budget prevents ask. A missing configuration returns abstain with an
explicit not_configured status. Report mode is an explicit separate pure-core
option; the compatibility API's report-selection behavior is unchanged. No
operating point is implicitly installed by the new code.

`ranker_port.py` is the only investigation import of retrieval/ranking internals.
It wraps the unchanged Mid-I service and optionally delegates to V1's future
`retrieval.service.rank`, preserving its actual version. Missing V1 emits an
explicit fallback warning; broken installed dependencies are not swallowed.
The old graph API cannot enforce an as_of bound, so the port refuses to ignore
one. Offline experiments provide a prefiltered graph instead.

## Runtime and persistence

Stateless Copilot now has additive beliefs, policy inputs and ranker metadata;
all frozen fields retain their behavior, including null reply on model outage.
Persisted sessions still supply the outage template. New snapshots save beliefs
on hypotheses and entropy; full saved responses retain the exact derived inputs.
Old snapshots/replies continue to replay without enrichment or recalculation.
Runtime stays uncalibrated/unconfigured until selected parameters are accepted;
structured answers still need the question package and are refused meanwhile.

## Offline protocol

`experiments/download_projection.py` streams official FAA 2023/2024 CSVs into
compressed, git-ignored inputs with canonical projected-row SHA-256 metadata.
It does not replace or edit Umar's corpus builder. Held-out 2025 download and
source overwrite are refused by this preparation command.

`offline.py` also accepts the contract's processed CSV columns. Dates are aware
SubmissionDate timestamps; occurrence dates define split years. Invalid timestamps
and ambiguous repeated IDs are excluded and counted. Explicit supplemental
citations must refer to an existing record on the same nonempty tail and a
strictly later submission. Every eligible known-outcome pair is retained. Empty/
unknown correction parts are counted as excluded labels, not invented causes.
All connected citation-chain records and equal/later submissions are excluded
from every query; the actual read adapter enforces this on every access. Original
text supplies symptoms; the correction part is used only as the outcome label.
Supersession status changes only when a correction is visible at query time.

The bounded Mid-I ranker still scans at most 2,500 visible fleet records and 30
asset records. Offline equal-occurrence ties use record ID descending for stable
input; live Mid-I Cypher has no secondary tie key. That methodological difference
is disclosed. No retrieval weights or other owners' code are changed.

`calibration.py` fits temperature/other score by bounded-grid NLL minimisation on
2023, with six deterministic refinements and recorded domain/boundary diagnostics.
The shared contract's 2023 fit wins over the guide's conflicting 2024 fit sentence.
`decision_benchmark.py` fits 2023 before loading selection data, produces a 2024
threshold table, fingerprints sources/method code and records dirty-tree status.
`abstention_curve.py` reports top-1/top-3 accuracy on answered cases, coverage and
unsupported top-3 outcome-key rate over all cases. The baseline removes both
confidence and evidence gates, with empty rankings still unanswered. ECE uses
ten equal-width bins for the leading named belief. 1,000 bootstrap draws cluster
pairs sharing an original report; undefined answered accuracy stays null.

The current benchmark is selection before the question policy, not final RQ4
performance. Question-policy effects are now measured separately in [the question package](investigation_questions.md). No selected operating point or 2025 result is claimed.
