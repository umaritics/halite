# FYP-1 Mid report (LaTeX source)

Build with [tectonic](https://tectonic-typesetting.github.io/) (`brew install tectonic`):

```sh
./build.sh          # writes build.pdf
python3 gen_appendix_tests.py   # regenerates Appendix C from the real test runners
```

Notes
- `build.tex` declares `\pdfcompresslevel` before loading `main.tex`; the university class uses a pdfTeX-only primitive and tectonic runs XeTeX.
- `main.tex` adds the packages the template uses without loading (`longtable`, `booktabs`) and defines `\projecttitle`, `\studentone` ... which the template's submission page uses but never defines.
- Layout: `openany` (no blank pages before chapters), floats allowed to move (`[htb]`), table text one size smaller (`\tablefont`), and the class's empty `\null\vfill` after the cover removed (it created a blank page 2).
- Yellow `[CONFIRM: ...]` markers must all be resolved before the PDF is submitted: `grep -rn confirm chapters/`.
- Submission file name: `F26_<group>_i230711_i230782_i230585.pdf`.
- Figures are TikZ in `figures/`; screenshots are read from `../screenshots/`.
- Every count in the report is traceable: test counts to CI run 39068741787 on commit `36a98a3`; commit counts to `git` at that commit; the evaluation numbers to `docs/evaluation_results.md`.
