---
id: DEC-20261124-integrity-masked-benchmark
title: Citation-masked benchmark for unannounced corrections
status: partly accepted / proposals pending (Shahmeer)
owners: [Shahmeer]
updated: 2026-11-25
---

# DEC-20261124 — Citation-masked benchmark

## Context

Rule R1 links announced corrections ("SUPPLEMENTAL REPORT FOR (id)") without a model. A report can also correct an
earlier one without saying so. That case needs the model, and we have no labels for it at scale.
Every announced pair is a label if the announcement is hidden. The benchmark in `backend/integrity/bench/` does that.
Commands and file formats: [bench README](../../backend/integrity/bench/README.md).

## Decision

1. **Mask the announcement, and measure the unannounced case.** The newer report's citation and the cited id are removed
   from every text the model can see. The prior is masked too, because a prior can itself be a supplemental report.
   Every `*` is removed in both maskings: FAA bold marks wrap the announcement, so a leftover seam would give the label away.
   - Not taken: test on the announced text. The model would read the citation, and the number would not describe the case R1 cannot handle.
2. **Two maskings, both built.** M1 removes the citation and the id. M2 also removes the "supplemental report will be
   submitted" sentence and the `(OPEN)` and `(CLOSED)` markers, which show how far a report is along its life.
   Both are built for 2023 and 2024.
3. **Chain members are excluded from negatives.** A report that cites or is cited by the new report's chain is a near-copy.
   Scoring a correct `supersedes` on it as a false link would punish the model for being right. Hard negatives skip chain members.
   Hard negatives and presumed negatives are also skipped when the raw texts name each other or name the id the new report cites.
   The counts dropped are in each manifest.
4. **Presumed negatives are presumed.** A presumed negative is a report that cites nothing, is cited by nothing and has at
   least one candidate, paired with its top containment candidate. Some may be unannounced corrections, which would count
   a correct link as a false one. The builder exports 50 of the presumed negatives in each bench file, unmasked, to
   `presumed_negatives_check_<year>_<masking>.csv`. Shahmeer marks them by hand, so the label noise of the scored pairs can be estimated. Reports that carry a correction phrase the citation
   parser misses are left out of the pool, and the manifest counts them. Presumed negatives follow the operator mix of the
   positives, so template style cannot predict the label.
5. **Candidates are knowledge-time candidates.** A prior is a candidate only if it was submitted strictly earlier than the new
   report (`timeutil.is_eligible_prior`). A citation to a report submitted later is rejected as a label
   (`prior_submitted_later`, counted in the manifest). Without this, the benchmark would use facts the engine could not have had.
6. **The deployed history cap is measured, not silently fixed.** Staging reads the oldest 200 reports of an aircraft
   (`list_asset_history(limit=200)`). A newer report on a busy aircraft could lose its true prior to that cap.
   The builder keeps the cap by default (`--history-limit 200`) and records `positives_hidden_by_history_cap` in the manifest.
   Stage 1 also reports the `ranks_capped` hit rates next to the uncapped ones. Changing the cap in the engine is a separate decision.
7. **The 2025 split is locked.** Splits mirror CONTRACTS 4.4: 2023 fit, 2024 select, 2025 test. Building or running 2025 is refused
   unless `--unlock-test "<reason>"` is given, and each opening appends a line (file, model, prompt, reason, commit, time) to
   `bench/results/test_split_log.jsonl`. Builds of earlier years never read a later year's file.
8. **Stage 2 is scored three ways from one set of model answers.** `model` and `cascade_as_deployed` treat every pair as
   having reached the model. `deployed_end_to_end` does what staging does today: only the first candidate in the containment
   order reaches the model (defect D8), then the screen. A true prior that is not first counts as missed. The first two
   say how good the classifier is; the third says what the deployed pipeline would have linked.
9. **Intervals resample new reports.** A positive and its hard negatives share the new report's text, so they are drawn
   together in the bootstrap. Resampling single pairs would give intervals that are too narrow.
10. **Prompt v1 is pinned; v2-unannounced is a draft.** `v1` is the staging prompt, pinned by a hash test. `v2-unannounced`
   drops the word "explicit" from the definition of `supersedes`, for unannounced corrections. It is used only by the benchmark.
   Staging keeps `v1` until Shahmeer decides.

## Scope found in the data

- **One operator.** In the 2023 and 2024 FAA files every report that carries "SUPPLEMENTAL REPORT FOR (id)" has an id starting
  `AALA` (432 of 432 citing reports in 2023, 401 of 401 in 2024). That operator files about 14% of the 2023 rows and 15.5% of
  the 2024 rows. All positives, hard negatives and presumed negatives in the four bench files are `AALA` reports
  (`operator_mix` in each manifest). A benchmark result therefore describes this operator's reports. Whether other operators
  correct reports without announcing it, and how those corrections read, is not measured.
- **Hard look-alikes are real.** In the 2024 M2 file 97 of 396 presumed negatives share the occurrence date with their prior
  and repeat at least 80% of its tokens. Reading a few shows templated findings from one maintenance visit that differ in a
  position or a row number. Some may be unannounced corrections; that is what the 50-row hand check is for.
- **Unparsed announcements.** Some reports announce a correction in a wording the parser does not read ("SUPPLEMENTAL REPORT
  REQUIRED FOR", "FOR SDR <id>", misspellings, "ORIGINAL REPORT WAS <id>"). They are neither positives nor negatives here:
  77 reports in 2023 and 221 in 2024 were left out of the presumed-negative pool for this reason. Rule R1 does not link
  them either. Widening the parser is a separate decision (it is shared with the other verticals).

## Proposals awaiting Shahmeer (guide section 6) — not decisions

- **M2 as the primary masking.** Proposed because it is the stricter one. Until Shahmeer decides and writes why, neither masking is primary.
  The stage 1 files below are reported for both.
- **alpha = 0.02.** Proposed. Not adopted, not used by any code in this work. `alpha` and `beta` are Shahmeer's call.

## Stage 1 results (2023 fit, 2024 select; no model)

Source: `backend/integrity/bench/results/candidates_2023_M1.json`, `candidates_2023_M2.json`, `candidates_2024_M1.json`,
`candidates_2024_M2.json`. Values are copied from those files and rounded to one decimal place. Brackets are 95% bootstrap
intervals (1,000 resamples of new reports, seed 20261124). The set is positives only, using the `ranks` set (uncapped, chain members counted).
These are fit and select numbers. They are not test numbers.

Pairs: 2023 has 428 positives, 444 hard negatives and 428 presumed negatives. 2024 has 396 positives, 499 hard negatives and 396 presumed negatives (same in M1 and M2).

| Year | Masking | Ordering | Top 1 | Top 3 |
| --- | --- | --- | --- | --- |
| 2023 (fit) | M1 | legacy | 74.5% [70.8, 78.5] | 94.9% [92.8, 97.0] |
| 2023 (fit) | M1 | containment | 90.4% [87.6, 93.0] | 98.6% [97.4, 99.5] |
| 2023 (fit) | M1 | submission_gap | 65.9% [61.2, 70.3] | 90.0% [86.9, 92.5] |
| 2023 (fit) | M2 | legacy | 74.5% [70.8, 78.5] | 94.9% [92.8, 97.0] |
| 2023 (fit) | M2 | containment | 91.4% [88.8, 93.7] | 98.6% [97.4, 99.5] |
| 2023 (fit) | M2 | submission_gap | 65.9% [61.2, 70.3] | 90.0% [86.9, 92.5] |
| 2024 (select) | M1 | legacy | 64.9% [60.1, 69.2] | 89.4% [86.4, 92.4] |
| 2024 (select) | M1 | containment | 91.7% [88.9, 94.2] | 97.5% [95.7, 99.0] |
| 2024 (select) | M1 | submission_gap | 63.6% [58.8, 68.4] | 86.9% [83.6, 90.2] |
| 2024 (select) | M2 | legacy | 64.9% [60.1, 69.2] | 89.4% [86.4, 92.4] |
| 2024 (select) | M2 | containment | 91.9% [89.4, 94.4] | 97.5% [95.7, 99.0] |
| 2024 (select) | M2 | submission_gap | 63.6% [58.8, 68.4] | 86.9% [83.6, 90.2] |

How to read it:

- In 2023 (fit) and 2024 (select), under both maskings, the containment ordering puts the true prior at rank 1 more often than
  legacy, and the intervals do not overlap. The files also hold top 5, "anywhere", and the `ranks_ignoring_chain` set.
- In all four files `prior_not_a_candidate.share` is 0.0 and `hidden_by_history_cap_share` is 0.0. So on these two years the
  deployed cap hid no true prior, and the hit rates measure ordering, not retrieval. `ranks_capped` equals `ranks` in all four files.
- The number of candidates per positive (2023 fit: median 2.0, p90 11; 2024 select: median 3.0, p90 9) is in the files.
  Whether to classify the top 3 instead of the top 1 is not decided here. It triples the model cost, and the model has not been run.
- The metadata of all four files records git commit `3160c6d` and `git_dirty: false`, with the bench SHA-256 and manifest SHA-256, so the bench can be rebuilt and checked.
- Read with the chain set: a sibling supplemental of the same original often sits first. Ignoring chain members, containment puts
  the true prior first in 94.9% [92.8, 96.7] (2023 fit, M1), 95.1% [93.0, 96.7] (2023 fit, M2), 95.2% [92.9, 97.2] (2024 select, M1)
  and 95.5% [93.2, 97.5] (2024 select, M2) of positives (`ranks_ignoring_chain` in the same files).

## What has NOT been done

- **No model run yet.** `phi4-mini` is not installed on the development machine. No stage 2 result (precision, recall, F1,
  false-link rate, parse failures, seconds per pair, calls per pair) exists for any year, masking, prompt or mode.
  No `classify_*.json` file is committed. The runner is tested with a fake model only.
- **No 2025 run.** No 2025 bench has been built. `test_split_log.jsonl` has no lines. No 2025 number exists.
  The 2025 FAA file was downloaded on 24 November 2026 with Shahmeer's approval and is kept unopened outside the build folder.
  Its SHA-256 is `1b2ca9bc234fb978a2e3494386621897d5bd0ecb4e5fff62da494e015adba7e7`. A 2025 run must use a file with this hash.
- **The runner has met a real endpoint once, as a plumbing test only.** Fifteen 2024 pairs were sent to a small model that
  happened to be installed, to prove the OpenAI-compatible path, the resume file and the three systems work. Nothing from it is kept.
- **The protocol note is not written.** The one-page protocol note is written only by Shahmeer, and it is still to be written
  before any 2025 number is produced. Until then nothing may be run on 2025.
- **The 50-row hand check is not done.** The label noise of presumed negatives is therefore not estimated.
- **v1 against v2-unannounced on 2024 has not been compared.** That needs the model.
- No prompt on staging has changed. The engine's behaviour is unchanged.

## Consequences

- `backend/integrity/candidates.py`, `prompts.py` and `classify.py` hold the candidate ranking, the prompts and the votes.
  The engine calls them (see [conflict_engine.md](../context/modules/conflict_engine.md)). No behaviour change.
- WP-A2 is not complete. Stage 2 on 2024, then 2025 once, remain.
- Stage 2 reports three systems. Two treat every pair as having reached the model; `deployed_end_to_end` counts stage 1 misses.
  Each says which it is (`assumes_every_pair_reaches_the_model`).
- The benchmark measures a masked proxy. A pair that had a citation may differ from a true unannounced correction in ways masking
  cannot remove. Results describe the proxy.

## Owners

Shahmeer (Record Integrity). Built by an orchestrated run of coding agents and reviewed before merge.

## Date

2026-11-25
