# Phase 11 — source-word highlighting verified

PR [#41](https://github.com/umaritics/halite/pull/41), source `4136fc3`, hosted
workflow [44858279238](https://github.com/umaritics/halite/actions/runs/44858279238).
All jobs passed. This completes the source-word interaction implementation and
verification; it does not complete human grounding calibration or the full goal.

## Implementation

- `backend/investigation/grounding.py`: adds versioned UTF-16 source-body token
  locations to each candidate audit. Excludes citation IDs; retains repeated
  words, negation and quantities. Scores, guards and ratings remain unchanged.
- `SourceNarrative.jsx`: validates encoding, bounds, ordering and actual substring
  before rendering escaped source-word marks. Exact narrative text is preserved.
  Invalid or absent annotations do not create guessed locations.
- `DecisionView.jsx`: sentence hover and keyboard/citation focus select the
  corresponding saved source; uncited sentences clear stale source selection.
- `QuickDiagnose.jsx` and `InvestigationWorkspace.jsx`: show those marks in the
  saved source, bind selection to the correct turn and clear stale state. Old
  saved audits replay without recomputation. Highlights are labelled word overlap.
- Backend/UI tests and hosted browser verifier cover annotations, rendering and
  actual persisted replay. The three-record Unicode fixture is explicitly synthetic.

## Executed evidence

Four standard-library source-span tests passed locally in 0.003 seconds from
`backend` with `python3 -m unittest discover -s tests -p test_grounding_source_spans.py -v`.
No local dependency installation, browser, container or model workload was used.

Hosted verification passed:

- 449 backend tests, runtime-error lint and SQL/graph-backed regression.
- 279 frontend tests, production and independent feature-preview builds.
- Neo4j/PostgreSQL/session smoke and production Chromium verification.
- Real authenticated quick diagnosis and persisted session turns in both themes.
- Exact source text and marked substrings, including offsets after an emoji.
- Exact saved grounding JSON after reload; hover and keyboard citation selection.
- Saved evidence at 1280px and 390px, no horizontal page overflow/browser errors.

Screenshots, combined browser proof, filtered test output, source SHA, job URLs
and file checksums are retained in `evidence/phase11-source-highlighting/`.
Visually inspected quick-source dark/light, saved-evidence desktop dark and
phone light screenshots. The complete source and both highlighted words remain
readable; phone identifiers/part names wrap within the card.

The first browser run used a login token invalidated by page-reload refresh
rotation. The verifier now follows the browser's current actual bearer token,
kept in process memory only. Product authentication was not weakened or changed.

## Remaining gates and disclosure

Backend coverage is still 78% on the broad measured scope; 80% remains open.
Independent labels/threshold acceptance, operating-point acceptance, held-out
evaluation, model measurements/choice, owner review, merge and release are not
asserted complete. See `ACCEPTANCE_MATRIX.md`. This proof is disposable local-to-
runner full-stack execution, not a claim that staging has these review branches.

AI assistance: Codex implemented, tested and documented these changes.
Student/owner review: Usman understanding/review and independent human calibration
remain required; no labels, review or sign-off were fabricated.
