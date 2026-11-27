# Bound runtime explanations on the existing CPU model

Status: prepared; focused tests passed; hosted and live acceptance pending

Owners: Usman

Date: 2026-11-22

## Context

Actual dedicated-account session and quick diagnosis reached their120-second
provider deadline. Persistence, fallback, closure and report HTML worked, but
health configuration alone did not prove a successful live explanation. The
session prompt was15,259bytes with2,400output tokens. Existing reference traces
also show material CPU prompt-processing time; increasing the client deadline
alone would not make interactive requests responsive.

## Decision

Use a pure2,048-byte/192-token prose builder with three prioritized report
excerpts. Keep complete response ranking, case state, all saved evidence and
record identity intact. Record exact supplied/available IDs, excerpt status,
prompt hash/version and whether model text was actually accepted. Show a source-
coverage warning. Validate citations and sentence membership against the actual
model sources; templates and deterministic answers retain their correct saved
source boundary. Do not let a model choose questions, procedures or decisions.
Remove previous model provenance on structured answers.

Keep quick-diagnose JSON source lists/schema, bound explanatory wording and output
budget, and withhold malformed structured fragments. Reject provider-marked
token-cutoff prose in both adapters; JSON classifier behavior stays unchanged.
Version runtime prompts/cache identities. Do not change model, CPU/memory caps,
frozen research methods, selected thresholds or benchmark generation settings.

## Consequences

The natural-language reply explicitly covers a supplied subset; all complete
sources remain available in saved evidence and the printable report. The model
must state missing detail rather than infer omitted narrative. This is not a
claim of whole-corpus review, semantic accuracy or a general latency guarantee.
Real post-release default-session/quick checks and saved-browser replay/print are
required before accepting the fix. Retain both failed baseline attempts.

## Actual release observation

Sourceb9bad63 passed549backend tests plus frontend/full-stack and merged11beed1.
Default session still timed out (154.35s total) and quick diagnosis also returned
fallback (126.42s). Input/output bounds are enforced but do not establish latency
acceptance. Preserve them as explicit source-coverage bounds; investigate service
execution before claiming an availability fix. Public populated replay/closure/
one-click printing passed44993544541; PDF visual margins need a separate fix.

The separate print correction merged/deployed via PR56, with actual browser
44994441004 and all4PDFpages visually reviewed. All20full saved narratives
retained. This independent printing acceptance does not change the two failed
model-availability measurements. Initial clipping suspicion was disproved by
close-up inspection; zero-margin crowding was corrected.
