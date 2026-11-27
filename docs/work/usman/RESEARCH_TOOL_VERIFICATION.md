# Research artifact tools and exact coverage — verified

Source commit: `c5d279a` (PR #44).
[Successful full hosted run](https://github.com/umaritics/halite/actions/runs/44882587938).

All CI jobs passed: **453 backend tests**, **279 frontend tests**, Ruff, production
and feature builds, disposable Neo4j/PostgreSQL maintenance/session smoke and
production Chromium chart/source-highlighting verification.

## Evidence for NFR-04

**4,744 / 5,851 measured statements = 81.08%**. The six scopes remain `api`,
`agents`, `services`, `graph`, `db` and `investigation`; no source omission or
scope reduction was added. Compared with phase13, 88 additional statements are
exercised against the same denominator. CI now requires 80%, with two-decimal
precision; its terminal report explicitly confirms that the gate passed.
This is measured backend scope coverage, not an unsupported frontend/whole-repo
coverage claim. Owner review/merge remain pending.

## Meaningful verification added

Thirteen integration checks verify exact reproduction of all 71 committed FAA
code descriptions and fingerprints from the retained official archive, successful
checksum-matched CLI publication and refusal of changed provenance, both workbook
string representations/relationship paths, missing tables, bad headers, duplicate
codes and incomplete rows. They also execute the actual grounding vocabulary
fitter/command: normalization, unknown exclusion, source fingerprints, 2023-only
fitting, refusal of 2024/2025/empty corpora and preservation of previous output.

Synthetic workbook/CSV cases are explicitly test fixtures. They are not new FAA
meanings, human annotations, model results or held-out research evaluation.

## Retained proof

`evidence/phase14-research-tool-verification/` contains raw coverage XML, JUnit
(with all 13 test names), measured dependency summary, current browser proof,
terminal gate/test/smoke excerpts and commit/job/artifact-hash metadata. Full
screenshots and runner logs remain in the linked CI artifacts. Phase12/13 retain
the raw pip resolution/installed reports for the unchanged dependency stack.

Latest remote main was refreshed and remains `0dd86d9`. The laptop retained
24 GiB free, approximately 12 GiB available RAM and zero swap; all heavy work ran
on GitHub runners. No staging data, runtime thresholds or model selection changed.

Next phase prepares question-conditioned 2024 operating-point evidence. The full
acceptance matrix still retains human calibration/review, model measurements,
held-out evaluation, report and release gates.
