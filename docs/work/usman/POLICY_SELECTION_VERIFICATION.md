# Question-conditioned 2024 stopping selection — verified

Source: `28dcd3a`, PR #45.
[Full CI](https://github.com/umaritics/halite/actions/runs/44883665006) and
[selection + independent verification](https://github.com/umaritics/halite/actions/runs/44883664943)
are successful. The sweep checked out PR merge `9d526170956a59601292f51147e4be4d0822cfc0`
with a clean tree; its actual checkout is recorded in the artifact.

**461 backend tests**, **279 frontend tests**, lint, both builds, real disposable
Neo4j/PostgreSQL maintenance/session smoke and production Chromium flows passed.
Coverage is **4,892 / 6,018 statements = 81.29%**, above the unchanged six-scope 80% gate.

## Research evidence

The fixed 21-by-six grid was declared before results. It evaluates all three
attribute cohorts, information-gain/random/no-question strategies, three part-
change strata and all cases: **4,536 rows**. All cohorts retain the same **389
correction pairs / 340 originals**. Every stratum uses **1,000 shared original-
report cluster-bootstrap draws**. Undefined answered accuracy is null with a
valid-resample count. The saved trajectory is truncated only when actual policy
says answer/abstain; a later posterior never enters an earlier decision.

An independent scalar implementation recalculated every row's point metrics
without using the production stopping helper. Tests check hand-computed cluster
ratios/percentiles, gain equality, named evidence identity after reordering,
empty/padded traces, actual managed-controller parity, frozen-source refusal,
small-grid export and roundoff-versus-material-prior changes.

The initial sweep stopped on exact equality of recomputed softmax values across
platforms. The corrected validator permits only 1e-12 relative / 1e-14 absolute
roundoff; artifact hashes and saved trace bytes remain exact. Both corrected
workflows passed. No failed run is represented as success.

## Decision and retained proof

[OPERATING_POINT_REVIEW.md](OPERATING_POINT_REVIEW.md) presents a concrete
conservative proposal and alternatives with counts and 95% intervals. It remains
**unselected** pending Usman's answer; no runtime threshold is changed, no
probability wording is enabled and no 2025 data is read. Top-three misses remain
an outcome-key proxy rather than sentence hallucination or fault-cause truth.

Full JSON/CSV: `backend/investigation/experiments/results/policy_selection_2024_v1/`.
Protocol/source SHA pins: `backend/investigation/experiments/policy_selection_protocol.json`.
Raw coverage/JUnit, current browser proof, CI excerpts, independent verification
and commit/job/hash metadata: `evidence/phase15-policy-selection/`.

No package/model/database build ran locally. The full sweep ran on a one-thread,
20-minute-bounded GitHub job using the already pinned NumPy; no graph or model
endpoint was contacted. Owner review/merge/release and remaining human research
acceptance remain explicit gates in the acceptance matrix.
