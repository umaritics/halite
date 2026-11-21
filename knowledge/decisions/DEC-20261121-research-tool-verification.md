# Verify retained research tooling and enforce the exact coverage target

- Status: implemented and hosted verified on c5d279a; review/merge pending
- Date: 2026-11-21
- Owner: Usman

## Context

Retirement leaves broad backend coverage at 4,656/5,851 = 79.58%. The terminal
rounds to 80%, which is insufficient evidence for NFR-04. The official lookup
importer and grounding-vocabulary fitter were executed for artifacts but lacked
automated integration coverage of their critical provenance/isolation contracts.

## Decision

Test exact reproduction from the retained FAA archive, command checksum gating,
workbook variants and malformed/duplicate/missing tables. Exercise the actual
vocabulary fitter/command on explicit synthetic CSVs and verify no held-out input
or saved-output overwrite. Add the 80% pytest-cov gate and two-decimal report
precision, preserving the existing six measured source scopes with no omissions.

## Consequences

Tests provide useful reproducibility and error-path evidence; synthetic fixtures
never substitute for research outcomes or human labels. Coverage failure remains
a real CI failure with JUnit/XML artifacts. Hosted verification remains necessary
before claiming the target achieved. Heavy runs stay off the developer laptop.

Run 44882587938 passed all jobs: 453 backend/279 frontend tests, real database
and browser flows. Exact coverage 4,744/5,851 = 81.08% exceeds the unchanged-scope
80% gate. Raw coverage/JUnit, test names and job/hash proof are retained in
phase14 evidence and RESEARCH_TOOL_VERIFICATION.md.
