# Phase 10 — research results in the product

The research page turns the committed 2024 selection evidence into a reviewable
product flow. It does not install a policy, invent a selected point or evaluate
held-out data. This is one phase of the full FYP-I objective.

## Changes and review boundaries

- PR [#38](https://github.com/umaritics/halite/pull/38): user-authenticated
  `GET /api/sessions/experiments`; fixed artifact allowlist, SHA-256 publication
  manifest, compatible method/split/corpus and measurement checks, explicit empty
  publication, and 503 on unverifiable evidence. Exact measurements/provenance
  are preserved, with private/no-store responses.
- PR [#39](https://github.com/umaritics/halite/pull/39): isolated Recharts/shared
  chart/primitives preparation for Shahmeer review. Existing pages and shell are
  not refactored. The library is the one explicitly selected by the master plan.
- PR [#40](https://github.com/umaritics/halite/pull/40): investigation history links
  to `/app/investigations/experiments`, registered before the session-ID route.
  The page shows all three question policies, all three attribute controls,
  correction cohorts, top-1/top-3/entropy, paired intervals, accuracy–coverage,
  the outcome-key proxy and provenance. Shared wrapper accepts saved budget ticks.

## Acceptance evidence

- Pure publication integrity: twelve standard-library tests passed locally in
  0.100 seconds; no dependency install/model/container workload required.
- API PR #38 workflow [44745242226](https://github.com/umaritics/halite/actions/runs/44745242226):
  445 backend tests; 267 frontend tests; lint, builds and real-graph/session smoke
  passed. Real JWT, anonymous/service rejection, static-route ordering and
  corruption failure are tested.
- Shared foundation workflow [44746369647](https://github.com/umaritics/halite/actions/runs/44746369647):
  all jobs passed after correcting the test's missing browser media APIs.
- Product baseline `7aeddb2`, workflow
  [44747282289](https://github.com/umaritics/halite/actions/runs/44747282289):
  445 backend tests, 275 frontend tests, both builds and hosted real-browser
  verification passed. Downloaded screenshots were visually inspected in dark
  and light themes at 1280px, and at 390px phone width.
- Final discrete-axis assertion on `ecdc264`: workflow
  [44856875802](https://github.com/umaritics/halite/actions/runs/44856875802)
  passed every job, including the exact saved-budget assertion. Final screenshots,
  proof, job metadata and checksums are in `evidence/phase10-research-panel/`.
  The final light question chart and dark phone view were visually inspected.

The browser uses the production build, real JWT/API reads and exact committed
artifact checksums. It verifies three SVG charts with whiskers, saved-value table
parity, controls, deep-link reload, both themes, phone geometry and absence of
browser exceptions. Failure/retry/empty subchecks explicitly mock those responses;
they are not represented as real backend outages.

Visual inspection found fractional automatic budget ticks. The page now supplies
recorded budgets and the browser asserts every label against the saved artifact.
The first assertion used the wrong SVG layer; the published Recharts source
confirmed that tick labels live in their own layer, and the selector was fixed.

## Research honesty and unfinished objective gates

All plotted values come from committed artifacts. Each chart declares sample
size, original-report count, year and 95% cluster-bootstrap intervals. Undefined
answered accuracy is not changed to zero. Paired intervals crossing zero do not
claim a question-policy advantage. The unsupported rate is explicitly a top-3
outcome-key proxy over all cases, not a sentence hallucination/safety rate.

No operating point, accepted grounding thresholds, human labels, M4 measurements,
2025 result, owner review, merge or staging deployment is fabricated. Backend
coverage remains 78% on the broad measured scope; the 80% target remains open.
The full objective stays active in `ACCEPTANCE_MATRIX.md`.

## Knowledge bank and AI assistance

Context, flows, registry/index and publication decision are updated alongside
implementation. See `investigation_decisions.md`, `investigation_frontend.md`,
`research_charts.md`, `FLOW-research-publication.md` and the CI notes.

AI assistance: Codex prepared the implementation, tests, evidence and this note.
Student/owner review: Usman understanding/review and Shahmeer shared-file review
are still required; this note does not assert that either occurred.
