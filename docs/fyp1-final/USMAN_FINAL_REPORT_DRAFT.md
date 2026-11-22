# Investigation Sessions — FYP I final report draft

Author for submission: Muhammad Usman Al Haq. Status: AI-assisted engineering
draft for the student's review and integration into the team report. This is not
evidence of independent authorship, supervisor acceptance or a completed defense.
All empirical claims below refer to retained measurements. Human grounding labels
and M4 model measurements have not yet been supplied.

## Contribution and scope

Halite supports maintenance investigation using historical service reports. This
vertical turns a transient conversation into a durable, user-owned investigation
and separates retrieval, deterministic decisions and generated explanations. Its
contribution comprises persistent sessions and outcomes, reproducible belief and
question snapshots, answer/ask/abstain decisions, sentence-audit infrastructure,
a home dashboard, printable reports and reproducible temporal experiments.
Backend preparation, dependency retirement and hosted quality checks support the
three project verticals. Retrieval weights and integrity judgments remain behind
their respective owners' interfaces.

An answer identifies historical support for a component hypothesis. It does not
identify a certified fault, authorize maintenance or establish airworthiness.
The evaluation's recorded correction-part key is an observable proxy for an
outcome, rather than independently adjudicated diagnostic ground truth.

## Design and rationale

The deterministic ranker supplies at most ten named hypotheses and evidence.
For named score s_i, temperature T and an additional other score c, beliefs are
b_i = exp(s_i/T) / (exp(c/T) + sum_j exp(s_j/T)); the remaining term is b_other.
The implementation uses stable softmax. The other bucket explicitly represents
support outside the retrieved candidate set. Temperature and c are fitted by
negative log likelihood on 2023 correction pairs, separately from threshold
selection. A ranker-version mismatch invalidates fitted parameters.

A high normalised score can still be wrong when retrieval omits the true part.
Consequently the product calls these values **relative support**. The test ECE
reported below does not justify describing them as calibrated probabilities.
Without fitted compatible parameters the fallback is explicitly uncalibrated;
without configured decision parameters the policy abstains.

The rule first answers if the leading named belief is at least tau_answer and
has at least two active evidence records. Otherwise it asks if an eligible
question has expected information gain at least g_min and the three-question
budget remains. Otherwise it abstains. For attribute A, information gain is
H(B) minus the expected posterior entropy over A's possible answers. Likelihoods
use the frozen historical attribute schema. The simulator answers from original
report fields; the correcting report is reserved for downstream scoring.

The user selected tau_answer = 0.80 and g_min = 0.50 bits after the 2024 joint
selection table. This expresses a preference for fewer wrong suggestions at the
cost of more unanswered cases. It does not assign a numerical financial or safety
cost to a wrong suggestion. A direct threshold on the raw ranking score would
ignore competition between candidates and vary with the ranker. Asking the model
to estimate confidence would entangle prose generation with the decision and
make replay less reliable. The explicit rule makes the trade-off inspectable.

The language model extracts observations and writes prose; it does not select
the question or decision. Prose calls and JSON extraction have separate adapter
formats. If the model is unavailable, persisted sessions retain deterministic
ranking, evidence and a marked fallback explanation. Existing stateless API
failure contracts are preserved unless the caller explicitly allows degradation.

## Persistence, access and explanation inspection

PostgreSQL stores sessions, turns and snapshots. A snapshot preserves the actual
beliefs, entropy, evidence IDs, question basis and answer history used at that
turn. Reload reads the saved response rather than reranking against a changed
graph. The session owner can write; supervisors and admins can inspect sessions
within their organisation without gaining ownership. Other users' IDs return
404. Service-key principals cannot create user sessions. Closed sessions record
the technician's observed outcome and provide an escaped printable report.

Sentence checks separate evidence membership from support. An existing report ID
outside the evidence supplied for that response is insufficient. Lexical checks
and an optional embedding port produce explicit audit states; saved UTF-16 word
spans let the interface highlight the exact stored source text on hover/focus.
An audit mark is not a human validation result. Valid citations remain unrated
by default until independent labels and threshold acceptance are complete.

The blinded calibration packet contains 150 sentence–report pairs, with 99 fit
and 51 validation items, to be labelled independently by Usman and Muhammad Umar.
These constructed FAA-text pairs do not substitute for generated-answer testing.
Agreement, adjudication and threshold tooling are implemented; observed precision,
recall and kappa must be inserted only after both real label exports are received.
L4 and generated-answer/no-evidence measurements remain separate evaluation work.

## Experiment protocol

The split is 2023 fit, 2024 selection and frozen 2025 test. There are 406 fit
pairs and 389 selection pairs from 340 original reports. Joint selection retains
4,536 rows across 21 answer thresholds, six gain thresholds, three attribute
pools, three question strategies and part-change strata. The user choice was
recorded before the successful test access. Test execution performs no fit,
threshold sweep, vocabulary fitting or prompt tuning.

Occurrence year defines the split. Every evidence read separately enforces a
strictly earlier submission time and excludes the query's connected citation
chain. A correction supplies the outcome key only after the question path is
complete. Original-field answers are simulated availability, not observations
from real technicians. The unchanged bounded ranker scans at most 2,500 visible
fleet records and 30 asset records; offline occurrence-time ties use a stable
ID order, unlike the live query's unspecified secondary ordering.

Four selection labels became available in January 2025. Their latest timestamp
was recorded before testing, with a predeclared post-cutoff sensitivity analysis.
All 157 test pairs occur after that cutoff, so the primary and sensitivity
results coincide. The earlier project ranker prototype had prior 2025 POC
exposure: this is a newly frozen-configuration temporal benchmark, not a claim
that the entire project had never seen any 2025 material.

One original 2024 source later gained a row. Before accessing 2025, a retained
identifier/order manifest reconstructed the original 66,080-row snapshot and
required its full original canonical hash. Changed or missing original content
fails closed. The additional row was excluded, not used to refit. The successful
run wrote a pre-access receipt before the first 2025 response and retained source,
procedure and parameter fingerprints.

Uncertainty uses 1,000 bootstrap draws clustered by original report. The same
cluster draws support paired comparisons; pairs sharing an original are not
treated as independent. Answered accuracy is undefined in resamples containing
no answers and reports its valid draw count. ECE uses ten equal-width bins over
leading named belief. Exact part-key match, question burden, coverage and
top-three outcome-key misses are reported separately from sentence grounding.

## Results

The selected 2024 joint rule answered 23/389 cases: 16 top-one and 17 top-three
matches, seven top-one misses and six top-three misses. Coverage was 5.91%
(95% CI 3.73–8.45%); top-one accuracy among answers was 69.57%
(47.62–88.89%). Mean question burden was 1.2622 per case. These are selection
measurements used for choosing the point, not the final test estimate.

The frozen 2025 test contains 157 pairs from 140 original reports. Both columns
below use identical terminal beliefs and simulated questions; the baseline
removes only the terminal abstention gate.

| Measurement | Frozen 0.80 / 0.50 rule | Abstention off |
| --- | --- | --- |
| Answers / cases | 7 / 157 | 157 / 157 |
| Top-one matches / answers | 5 / 7 | 31 / 157 |
| Coverage, 95% CI | 4.46% [1.32, 8.13] | 100% [100, 100] |
| Top-one accuracy among answers, 95% CI | 71.43% [33.33, 100] | 19.75% [13.66, 26.18] |
| Top-three accuracy among answers, 95% CI | 71.43% [33.33, 100] | 25.48% [18.40, 32.69] |
| Top-three outcome-key misses / all cases, 95% CI | 1.27% [0, 3.33] | 74.52% [67.31, 81.60] |
| Questions per case, 95% CI | 1.46 [1.35, 1.57] | 1.46 [1.35, 1.57] |

The accuracy intervals for seven answers use 999 valid bootstrap draws; one draw
had no answers. The other main intervals use all 1,000. Named-top ECE is 0.18364
(95% CI 0.13114–0.24616). Thus the selected rule answers much less often and
has fewer absolute outcome-key misses, but the seven answered cases provide
weak precision. This result does not establish deployment readiness.

At fixed budget two, information gain achieved 21.02% top-one match versus
12.10% for random questioning. The paired difference is 8.92 percentage points
(95% CI 3.07–14.67). At budget three, IG fell to 18.47%; more questions did
not monotonically improve ranking. Fixed-budget curves and the stopping-policy
result answer different comparisons. At the frozen stopping point coded-only
IG answered zero cases, so answered accuracy for that control is undefined.

The initial top ten omitted the outcome part in 113/157 cases (71.97%). Both
answered misses lacked the outcome candidate. All five correct answers were in
the same-part stratum; there were no correct answers in either changed-part
stratum. Reweighting a fixed candidate list cannot recover a missing candidate.
These errors identify retrieval coverage as the next development priority.

The [exportable frozen-results figures](figures/frozen-2025-results.pdf) present
these measurements as three vector pages: (1) the two fixed accuracy/coverage
points with saved intervals, (2) the three-control question-budget curves and
their saved intervals, and (3) descriptive part-change counts and retrieval
failure analysis. The export reads the frozen artifact without fitting,
simulation or bootstrap reruns. Its provenance and visual checks are recorded
in [FIGURE_EXPORT_VERIFICATION.md](../work/usman/FIGURE_EXPORT_VERIFICATION.md).

## Engineering verification and product presentation

Source 2247d17 passed hosted CI run 44911995235: backend and frontend suites,
lint, production builds, fresh Neo4j/PostgreSQL flows, frozen-input preflight,
saved-result replay and production Chromium checks. The source passed 500 backend and 283 frontend tests with
5,264/6,433 = 81.83% core coverage; raw reports are retained in phase-19 evidence. The earlier publication source 2af4d97
passed 499 backend and 283 frontend tests with 5,264/6,433 = 81.83% core coverage.
Coverage applies to the configured six source scopes, not every repository line.

The authenticated research page reads committed, hash-checked measurements and
shows denominators, years, intervals and the accepted 2024 marker. It labels 2025
as a fixed test and does not invent a test threshold sweep. Tests cover both
themes, desktop/phone widths, exact artifact parity and saved source spans.
CI browser acceptance uses an isolated hosted production build; public static
delivery and authenticated production acceptance are separate release evidence.

## FYP II plan for RQ4 and RQ5

For RQ4, retain the present result as immutable. Develop candidate expansion and
out-of-set rejection with the retrieval owner using a new development split,
then freeze a new untouched validation set before comparing revisions. Evaluate
retrieval recall separately from conditional reranking and abstention. Add actual
technician question availability and question time rather than assuming every
original-field answer is obtainable. Report both missed-candidate failures and
the coverage cost of rejecting uncertain cases.

Complete independent grounding labels, adjudication and held-out threshold
validation before accepting audit thresholds. Evaluate generated prose with and
without supplied evidence using the same frozen cases and model settings. Report
human sentence-support precision/recall, agreement, citation membership and
latency separately. A model judge is an additional measured signal, not a
replacement for the human reference. Record the actual M4 comparison before the
student chooses an interactive model; keep staging's phi4-mini unchanged meanwhile.

For RQ5, use consented, access-controlled closed-session outcomes as prospective
training cases. Freeze the trainer, curriculum and grading protocol separately
from diagnostic evaluation. Compare learning gains with a predeclared baseline,
pre/post assessment and participant-level analysis. Do not report training
effectiveness from historical correction-pair accuracy or synthetic conversations.

## Traceability and submission gates

Design: `DECISION_LAYER_DESIGN.md` and `OPERATING_POINT_DECISION.md`.
Protocol/results: `../work/usman/FROZEN_POLICY_VERIFICATION.md`,
`POLICY_SELECTION_VERIFICATION.md`, `HELD_OUT_VERIFICATION.md` and
`FINAL_RESEARCH_PUBLICATION_VERIFICATION.md` in that directory.
Raw test-year tables/traces/receipt/verifier:
`../../backend/investigation/experiments/results/held_out_2025_v1/`.
Full deliverable status: `../work/usman/ACCEPTANCE_MATRIX.md`.

Before submission, Usman must review and own the explanation, incorporate the
team's approved terminology and references, supply genuine grounding reviews,
transfer the confirmed no-comments Mid-I account into the official Form 10,
obtain any required supervisor confirmation and rehearse the defense. Teammate
cross-review is not inferred from the user's authorization to merge. AI helped
implement, document and verify the contribution; no fabricated human labels,
model timings, supervisor signatures or rehearsal outcomes are included.
