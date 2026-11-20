---
id: mod-research-charts
title: Shared research chart preparation for owner review
status: proposed
owners: [Shahmeer, Usman]
updated: 2026-11-20
---

# Chart foundation review proposal

The master plan explicitly selects Recharts as the only chart library. This
separate review branch prepares that dependency's lock metadata, a shared
`frontend/src/components/ui/ResearchChart.jsx` and minimal page primitives in
`ResearchPrimitives.jsx`. It does not refactor existing pages or the shell.
Shahmeer owns the shared files; his review/merge is required, not claimed.

The chart wrapper fixes role colours across product charts, uses asymmetric 95%
interval whiskers, disables animation of measurements, and requires sample size,
original-report count, year, bootstrap count and a methodological caption.
Both horizontal and vertical intervals are supported for accuracy–coverage.
An expandable HTML table preserves exact display values and undefined accuracy;
null estimates are omitted from the plot and never converted to zero. Text uses
existing theme classes, and a visible labelled legend does not rely on colour.
Product pages supply saved values; this component performs no inference.

Official Recharts reference: https://recharts.github.io/en-US/api/ErrorBar/
(absolute endpoints must be converted to distances from each estimate).

Targeted tests check asymmetric conversion and accessible undefined-value output.
Full build/tests and later actual product-page browser checks run in hosted CI.
