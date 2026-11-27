# Editable investigation chapter

Prepared `docs/fyp1-final/USMAN_INVESTIGATION_CHAPTER.docx` and its matching PDF
for Usman's review and integration into the team report. These are his contribution
chapter, not an approved university report or an end-of-session handoff.

The builder reads the retained Markdown chapter, verified reference companion
and three saved frozen-result figures. It adds a short opening synthesis,
plain-word headings and page numbers; converts the beliefs formula to two native
editable Word equations; preserves the exact results table; separates five
bibliography entries with working publication links; and appends the figures on
three landscape pages. Core report text remains editable. Appendix chart images
are saved PNGs; their separate vector PDF remains the scientific export.

## Executed verification

- Generated with the bundled Python document runtime, without package installs.
- Rendered using the skill's `render_docx.py` and bundled LibreOffice:
  `/home/muhammadusmanalhaq/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`.
  The user's desktop LibreOffice was not used.
- Inspected all eleven final page PNGs, including both equations, the complete
  results table, every bibliography entry and all three figure pages.
- Corrected inherited title-border decoration and collapsed bibliography entries;
  rebuilt, re-rendered and inspected the entire final document.
- Verified native OMML equation count (2), embedded figures (3), exact source-table
  parity, five separate reference entries, absent paragraph borders, all eleven
  page numbers, source/builder/output hashes and page sizes.
- Accessibility helper: zero high, medium or low findings. This is a structural
  audit, not a claim of testing every screen reader or Microsoft Word version.

Evidence: `evidence/phase24-editable-report/{export,verification,accessibility}.json`
and all eleven final page PNGs. Canonical DOCX/PDF hashes are in verification.json.
The export pins its input-source revision separately from the later builder hash.

## Regeneration

Use the bundled Python returned by the workspace dependency loader, then the
document skill renderer. `--revision` is the exact revision containing the source
chapter/references/figures, used for portable repository hyperlinks.

```sh
python docs/work/usman/build_report_chapter.py \
  --output output/docx/usman-investigation-chapter.docx \
  --manifest docs/work/usman/evidence/phase24-editable-report/export.json \
  --revision ab1d8eacad8fa1c730b754e7ba6d6da7323e5135
```

Re-render and review every page after any source, layout or OOXML change. Do not
reuse this verification record for a regenerated file without checking its hash.

No new empirical experiment was run. Actual labels, M4 comparison, generated-prose
and L4 evaluation, owner review, official-form confirmation, student acceptance
and a real defense rehearsal cannot be inferred from document formatting.
