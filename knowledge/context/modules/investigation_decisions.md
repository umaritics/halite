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
Default runtime remains unconfigured unless explicitly enabled with a policy
file. Managed structured answers now use saved question snapshots; the selected
research point below is available without automatically activating production.

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
performance. Question-policy effects are now measured separately in [the question package](investigation_questions.md). The selected research operating point is recorded below; no 2025 result is claimed.

## Published experiment reads

`GET /api/sessions/experiments` requires an active website-user JWT, independently
of the session database service. The static route precedes session-ID lookup.
`investigation/research_results.py` reads only the two fixed 2024 selection JSON
artifacts named in `experiments/results/publication.json`. SHA-256, method/split,
corpus compatibility, denominators and interval checks precede publication. The
response preserves exact measurements and provenance and is private/no-store.
A deliberately empty manifest returns an explicit empty state; missing/corrupt/
incompatible evidence returns 503, never substitute data. No inference, fitting,
graph query, policy activation or held-out read happens on this path.

The abstention rate is an outcome-key top-3 proxy, not a sentence-grounding rate.
Undefined answered accuracy stays null; the accepted operating point stays null.
The product page must retain those distinctions and display saved intervals.

## Question-conditioned stopping selection

`experiments/policy_selection.py` uses the actual `decide` rule on prefixes of
the checksum-pinned 2024 question traces. A threshold can stop a trajectory but
does not change the next deterministic question when continuation is permitted.
Named posterior ties keep original rank order and evidence counts remain attached
to their named hypothesis. Scoring receives the correction key only after the
stopping path is complete. The versioned protocol fixes 21 answer thresholds, six
gain thresholds, two-record evidence and three-question budgets before results.
All three attribute cohorts, three strategies and three part-change strata plus
all cases are retained. Random uses the selected random question's gain as an
explicit control; information gain is the managed-runtime path.

Original-report cluster resampling uses identical draws for every grid point and
strategy in a stratum. Undefined answered accuracy stays null and reports valid
resample counts. Metrics include coverage, answered top-1/top-3 accuracy, outcome-
key top-3 unsupported proxy and mean question burden over all cases. An independent
scalar verifier recalculates all point metrics; tests check hand-computed cluster
ratios and parity with the actual managed question controller. Numeric selection,
activation and 2025 evaluation remain separate decisions.

Joint stopping selection is verified on 28dcd3a: 4,536 rows / 389 pairs / 340
originals, with 1,000 bootstrap draws and independent scalar metric replay. See
POLICY_SELECTION_VERIFICATION.md. Usman explicitly accepted the 0.80/0.50 research point after reviewing counts
and intervals. The frozen choice is in params/selected-policy-v1.json; bars
remain relative support and 2025 remains untouched pending the frozen procedure.

## Accepted point and held-out preflight

The user explicitly answered “Freeze 0.80 answer / 0.50 gain (Recommended)”.
`docs/fyp1-final/OPERATING_POINT_DECISION.md` records that decision and AI-assisted
rationale. The selected policy pins the decision, exact accepted 2024 row, fit/
schema/codebook, method sources and label-availability audit. The held-out
protocol pins the policy; `experiments/frozen_policy.py` verifies both before
held-out work. Tests reject changed sources, thresholds, wording, refit/sweep
flags, missing metrics or shifted chronology. This does not activate runtime.

A verified pre-test audit of the frozen 2023/2024 projections found all fit labels
by April 2024, but four selection labels in January 2025 (latest 2 January).
Primary test cases retain the occurrence-year definition. A predeclared
sensitivity stratum contains only queries after the latest selection-label time;
report overlap and separate intervals rather than claim a wholly prospective
calendar split. No 2025 projection is read in the preflight.

Frozen choice/preflight is hosted verified on b97954d / run 44903750796: 476
backend/279 frontend tests and full database/browser flows pass; coverage 81.37%.
Hosted preflight fingerprints match committed policy/protocol files. See
FROZEN_POLICY_VERIFICATION.md; actual held-out execution remains next.
