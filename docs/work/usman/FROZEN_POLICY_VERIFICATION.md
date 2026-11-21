# Accepted research point and pre-test freeze — verified

Source commit: `b97954d`, PR #46.
[Successful hosted run](https://github.com/umaritics/halite/actions/runs/44903750796).

Usman explicitly selected **0.80 answer threshold / 0.50-bit minimum gain** after
reviewing the 2024 alternatives. The point keeps n_min=2, max_questions=3 and the
all-attribute information-gain strategy. The user answer and AI-assisted rationale
are recorded in `docs/fyp1-final/OPERATING_POINT_DECISION.md`.

## Verification

All jobs passed: **476 backend tests**, **279 frontend tests**, Ruff, both builds,
disposable Neo4j/PostgreSQL maintenance/session smoke and production Chromium
research/source-highlighting flows. Coverage is **4,958 / 6,093 = 81.37%**, passing
the unchanged-scope 80% gate.

Fifteen new checks cover the exact accepted row, actual managed-controller
compatibility, disabled default activation, unchanged artifacts, modified source/
decision/timing files, alternative thresholds, probability wording, refit/sweep
flags, missing metrics and shifted sensitivity cutoffs. Hosted CLI preflight
passed and records the actual policy/protocol SHA-256 values.

The selected file pins the 2024 row/table, decision, fit/schema/codebook, relevant
method sources, timing audit and its reproducible tool/preflight implementation.
All pinned fingerprints were checked against committed Git blobs. No runtime
setting was enabled and no 2025 archive was opened by this phase.

## Pre-test chronology audit

The retained `audit_label_availability.py` exactly reproduced the timing audit
from the existing frozen 2023/2024 projections, recomputing both canonical hashes.
All fit outcome labels arrived by April 2024; four selection labels arrived in
January 2025, latest 2 January. The primary occurrence-year evaluation remains
unchanged. Before test access, the protocol declares an additional stratum of
queries strictly after that latest label time, reporting overlap and separate
intervals. This distinguishes the occurrence-year experiment from a wholly
prospective calendar-time claim.

## Proof and remaining execution

`evidence/phase16-frozen-policy/` retains the label audit, raw coverage/JUnit,
actual hosted preflight JSON, current browser proof, CI excerpts and commit/job/
artifact-hash metadata. The selected policy and held-out protocol are under
`backend/investigation/params/` and `backend/investigation/experiments/`.

The research-point choice and freeze/preflight phase are complete. The next phase
must implement/verify and execute the frozen held-out procedure, retaining all
controls/strata, intervals, ECE and abstention-off comparison without tuning.
Publishing the accepted marker, remaining human/model/report acceptance and
owner review/merge/release remain separate requirements in the full matrix.
