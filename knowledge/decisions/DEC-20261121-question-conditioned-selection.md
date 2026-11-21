# Replay the actual stopping rule before choosing an operating point

- Status: implemented; hosted numeric verification pending
- Date: 2026-11-21
- Owner: Usman

## Context

The existing 2024 accuracy/coverage curve precedes questions; the separate
three-question comparison does not apply answer/gain stopping thresholds.
Selecting a live operating point therefore needs the combined policy evidence.
The full raw-corpus/ranking experiment need not be rerun: thresholds only stop
prefixes and never change a continued strategy's next question.

## Decision

Freeze input hashes and the 21-by-six threshold grid before results. Apply actual
production policy to saved 2024 prefixes using the original named evidence counts
and stable posterior order. Keep all three attribute cohorts, strategies and
part-change strata. Score keys only downstream. Use 1,000 shared original-report
cluster bootstrap draws with explicit null-accuracy counts. Verify point metrics
independently and hand-check bootstrap arithmetic and runtime controller parity.
Run the full sweep on bounded hosted infrastructure with pinned existing NumPy.

## Consequences

The output is selection evidence, not an accepted numeric operating point or a
2025 result. Random is an explicit selected-question-gain control; it is not the
managed production policy. Top-three key misses remain a proxy, not measured
sentence hallucination. Existing runtime/UI parameters and publication artifacts
remain untouched; human decision/review and held-out evaluation remain required.

Recomputed softmax priors use 1e-12 relative / 1e-14 absolute tolerance across
Python platforms. Exact saved traces (protected by input SHA pins) remain the
replayed source; material prior changes fail, and tests distinguish roundoff
from such changes. This does not relax any artifact fingerprint.
