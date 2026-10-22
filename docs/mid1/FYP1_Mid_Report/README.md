# Halite FYP-I Mid Report (final LaTeX)

Professional rebuild of the Mid-I report. Content and figure/table order follow `docs/mid1/reports/`; layout and styling do not.

## Build

From this directory:

```bash
pdflatex main.tex
pdflatex main.tex
```

Or:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

Requires a TeX distribution with `book`, `natbib`, `fancyhdr`, `geometry`, `enumitem`, `booktabs`, `longtable`, `microtype`, and Times (`mathptmx`).

## Layout choices

- Custom class `halite-mid-report.cls` (oneside, openany): chapters start on a new page without inserting blank even pages
- Margins ~2.2 cm; 11 pt Times; restrained chapter heads
- Page numbers bottom-centre on all numbered pages
- Roman front matter, Arabic body
- Diagrams kept as vector PDF clips under `illustrations/`

## Evaluated revision

Report claims are anchored to Git commit `36a98a3` (see Chapter 8 and Appendix D).

## Note on draft sources

`docs/mid1/reports/` remains the OCR/reconstruction draft. This folder is the submission-oriented source. Helper scripts `_build_clean.py`, `_strip_ocr.py`, and `_gen_appendix_c.py` are rebuild utilities only.
