# Frozen 2025 figure export

Three-page vector PDF: `docs/fyp1-final/figures/frozen-2025-results.pdf`.
The source is the already verified frozen 2025 artifact, SHA-256
`0815e2089902105e9c459ffe0afeffc664a1dc2039419ae415070b972b876a12`.

1. Two fixed accuracy/coverage points with the saved horizontal and vertical
   95% intervals. No threshold curve is invented; no line connects these points.
2. All three fixed-budget controls for top-one, top-three and entropy with saved
   intervals. The fixed-budget and stopping comparisons are explicitly distinct.
3. Actual stratum counts, initial candidate misses and relative-support ECE,
   with proxy and calibration qualifications visible on the page.

The exporter `plot_frozen_2025.py` checks the exact source hash, uses ReportLab's
standard chart primitives, and embeds Open Sans with font hashes in its manifest.
It reads saved values only: no new fitting, model call, simulation or bootstrap.
It requires ReportLab and Open Sans; the bundled document runtime supplied both
without installing anything on the laptop. An alternate font directory can be
provided with `--font-dir` (regular/bold OpenSans filenames are required).

```sh
python docs/work/usman/plot_frozen_2025.py \
  --output output/pdf/frozen-2025-results.pdf \
  --manifest docs/work/usman/evidence/phase23-report-figures/figure-export.json
```

Rendered every page with Poppler at 110 dpi and visually inspected all three.
The first draft exposed font substitution and text near the page boundary;
embedded fonts and measured width fitting corrected it. Re-rendered and inspected
every final page: no clipping, overlapping legends, missing glyphs or ambiguous
control labels. PDF text/page count checks and independent descriptive-count
crosschecks are retained in `evidence/phase23-report-figures/verification.json`.
The raw source rows, font/generator/output hashes and final PNGs are retained
beside that record. The Markdown report links the canonical PDF.

This is a verified presentation of an existing experiment, not a new empirical
result or evidence that the live policy is activated or safe for repair decisions.
