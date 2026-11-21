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
performance. Question-policy effects are now measured separately in [the question package](investigation_questions.md). The selected research operating point and verified frozen 2025 result are recorded below.

## Published experiment reads

`GET /api/sessions/experiments` requires an active website-user JWT and retains
private/no-store responses. Static route precedes session lookup. Publication v2
pins both earlier2024studies, joint stopping selection, frozen2025results and
independent verifier. Exact packaged policy/protocol, backend source pins, pre-
access receipt, denominator/interval/ECE/control validation precede publication.
Only saved rows at accepted gain are projected; no raw CSV, fit, sweep, ranking
or graph/model access occurs. Empty manifest is explicit; corrupt/incompatible
evidence returns503without substitute data. Earlier selected_operating_point
fields remain null as historical evidence; selected_policy separately records
the user's actual joint-selection decision. See final publication section below.

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
remain relative support; the subsequent frozen evaluation is documented below.

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
FROZEN_POLICY_VERIFICATION.md; subsequent actual execution is recorded below.

## Frozen held-out procedure

`experiments/held_out.py` validates the accepted choice and procedure hashes
before source access. It verifies historical projections against the frozen
2024 fingerprint before opening the 2025 archive and writes a pre-access receipt.
The dedicated downloader records source/projection and pre-access policy/protocol
fingerprints. Existing held-out sources need that matching receipt. No fitting,
vocabulary fitting or threshold search is called.

Evaluation reuses the unchanged bounded ranker, strict temporal/chain adapter,
2023 belief/schema files, original-report simulation and fixed stopping helper.
All pools/strategies/budgets/part-change strata and primary/post-selection-label
strata remain. Calibration is named-top ECE with ten equal-width bins on every
terminal case (including abstentions). Abstention-off retains exactly the same
terminal beliefs/questions and removes only answer gates. Raw traces support
independent scalar scoring and full interval replay.

The existing Mid-I ranker came from a prototype with an earlier 2025 POC. The
report therefore describes a frozen-configuration temporal benchmark rather
than a project-wide claim of no prior exposure to any 2025 report. Poor results
and retrieval misses remain visible; the accepted thresholds cannot be retuned.

The first real attempt stopped before 2025 because FAA appended one 2024 row.
All original history rows were verified unchanged. A compact identifier/order
manifest restores the exact approved snapshot and still requires its original
full canonical hash. Current downloaded revisions are archived; changed/missing
frozen content fails. The restoration is in the pre-access receipt and does not
refit parameters or add the new historical row to the research snapshot.

## Verified 2025 result

Source 5a5060b / hosted run 44906082558 completed the actual frozen test and
independent replay: 157 pairs / 140 originals, 72 stopping tables, all curves/
intervals/ECE preserved. The accepted all-attribute IG point answered 7 (5
part-key top-one matches, 2 misses) and abstained on 150, mean questions 1.4586.
Answered accuracy 71.43% has a wide cluster 95% interval 33.33–100% (999 valid
draws); coverage is 4.46% (1.32–8.13%). Abstention-off at identical terminal
beliefs/questions answers all 157 with 31 top-one/40 top-three matches. Named-top
ECE is .18364 (.13114–.24616). All test queries follow the predeclared latest
selection-label cutoff, so sensitivity and primary tables agree.

The true part was absent from the initial ten candidates in 113 cases, including
both answered misses. All five correct answers were same-part cases; coded-only
IG answered none. These results stay frozen and do not authorize tuning, live
activation or probability wording. Full CI passed 485 backend/279 frontend tests,
81.65% coverage and real disposable database/browser flows. See
docs/work/usman/HELD_OUT_VERIFICATION.md and retained held_out_2025_v1 artifacts.
The v2 product manifest now prepares the frozen test and accepted question-
conditioned selection for display; hosted publication verification passed on2af4d97/run44909092445.

## Read-only completed-research publication

Publication v2 retains both earlier 2024 studies and pins the full joint stopping
selection, frozen 2025 result and its independent verifier report. The endpoint
checks the real frozen policy/protocol, exact selection SHA/accepted row, matching
pre-access receipt, verifier/result SHA and all 72 control/stratum tables. It
validates denominator arithmetic, undefined intervals, equal chosen/off question
burden, calibration bins/ECE and question/stopping sample parity. The transport
projects only saved rows at accepted gain .50 (756 rows) from the full pinned
selection source. No refit, rerank, source download, threshold sweep or live
policy activation happens during reads. Missing/changed/incompatible evidence
returns 503; an explicitly empty manifest remains an empty publication.

Runtime packaging checks the actual backend policy/protocol and every pinned
backend input relative to the installed backend root. The backend-only Docker
image does not contain project docs. Full documentation/source preflight stays
in CI and remains byte-for-byte unchanged; publication does not require a fake
repository mount. An isolated backend-only package test and the real Compose
API/browser verify this boundary. Documentation/audit hashes remain provenance
in the frozen policy and are verified by the original CI preflight.
