# Saved word locations use browser-native coordinates

- Status: implemented; hosted verification passed (source 4136fc3, run 44858279238)
- Date: 2026-11-21
- Owner: Usman

## Context

The presentation standard requires sentence/source-word interaction. Recomputing
old audits would break exact replay, and Python code-point offsets differ from
browser offsets after non-BMP Unicode characters. Word overlap also cannot serve
as a new semantic support judgment.

## Decision

Add versioned UTF-16 source-body token positions to each new candidate audit.
Exclude citation IDs; retain exact text, repeated terms, quantities and negation.
Do not alter existing containment/guard/rating semantics. Save annotations with
the audit and render only validated substring/bounds matches as escaped React
marks. Sentence hover and keyboard focus select the same frozen source.

## Consequences

New saved turns support deterministic highlighting across reload and Unicode.
Old/invalid annotations retain plain source text with an explicit availability
message rather than reconstructed judgments. Human grounding calibration remains
a separate acceptance gate.
