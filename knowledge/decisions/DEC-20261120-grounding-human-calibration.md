# Sentence auditing without invented calibration

- **Status:** implemented; human calibration/acceptance pending
- **Owners:** Usman; independent second reviewer Muhammad Umar
- **Date:** 2026-11-20

## Context

The master plan requires L2 saved-evidence membership, L3 sentence support and
independent human calibration. No two real completed label files or accepted
thresholds exist. The repository has no actual retrieval embedding adapter.

## Decision

Attach additive, durable sentence audits to managed sessions and quick diagnosis.
Keep valid cited sentences `unrated` until an explicit configuration is supplied;
unknown citations still fail L2. Default to accurate lexical mode, preserve
original prose and saved evidence, and withhold dense-trained ratings if dense
encoding is unavailable. Use a frozen 2023 part dictionary and conservative guards.
Do not modify the frozen legacy citation extractor to support additional FAA ID
shapes; the new grounder recognizes actual mixed/numeric-leading IDs independently.

Prepare a reproducible blinded 150-pair constructed calibration packet from real
2023/2024 text. The user selected Muhammad Umar as the independent second reviewer.
Only actual human labels, with fingerprint, identity, time and rationale, enter
agreement/adjudication. Fit thresholds on 99 pairs and report 51 separate validation
pairs with disjoint original/reference IDs. Retain raw files and method hashes.
A fit proposal is never silently promoted to an accepted configuration or whitelist.

## Consequences

Sentence auditing and review tooling can be verified now. Synthetic browser/unit
labels exercise tools only and are never human agreement or generated-answer
accuracy results. The declared constructed sample needs a separate generated
answer/no-evidence/L4 evaluation before broader claims. Human review, operating
point and whitelist decisions remain genuine project gates, not inferred approval.
