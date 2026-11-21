# Shared research chart preparation — owner review

The master plan §3.2 selects Recharts and §11 requires Shahmeer's shared wrapper.
The shared frontend preparation has not landed. This isolated proposal adds only:

- Recharts dependency/lock metadata (no second chart library).
- `src/components/ui/ResearchChart.jsx`: shared role colours, saved interval
  whiskers, captions with year/sample size and an accessible values table.
- `src/components/ui/ResearchPrimitives.jsx`: the small set needed by the new page.
- Focused contract tests; existing pages/shell remain untouched.

Shahmeer review/merge is required. This is not a claim that his frontend
preparation is complete. The product page will be stacked on this proposal.
Undefined answered accuracy stays undefined, and absent accepted points will not
be marked as selected. Recharts API checked against its official documentation.

Verification: metadata-only dependency preparation and hosted tests/build.
No local full dependency installation or application/container build is run.

## Phase18 follow-up for review

The final publication needs a correct sample-stage label. ResearchChart now takes
optional `stage` with its existing `selection` default; the 2025 feature passes
`held-out`. This two-line shared-wrapper follow-up and its caption test are
prepared on the separate final-publication review branch. Colours, chart maths
and existing callers retain their behavior. Shahmeer review/merge is still
required; this preparation does not claim his approval. No shell file is touched.
