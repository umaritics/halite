# Frozen 2025 evaluation — verified

The user-selected research setting **answer threshold 0.80 / minimum gain 0.50 bits** was frozen on 2024 results and evaluated once successfully on the 2025 source. No fitting, vocabulary fitting or threshold search was performed on the test year. The default live policy remains disabled.

Source head: `5a5060b5e8bb54f1677be4acf93628dc89b03e0e`; executed PR merge: `237ab4115a19636e958302f67ac9be427517d5d7`.
[PR #47](https://github.com/umaritics/halite/pull/47) · [Full regression](https://github.com/umaritics/halite/actions/runs/44905815091) · [Actual evaluation and verification](https://github.com/umaritics/halite/actions/runs/44906082558).

## Main result

The test includes **157 known-correction pairs from 140 original reports**. The frozen all-attribute information-gain policy answered **7/157**, matching the recorded part in **5/7**; the other **150** were abstentions. These are exact part-key proxy outcomes, not confirmed fault causes, sentence-grounding scores or repair approvals.

| Measurement | Frozen policy | Abstention off at identical terminal beliefs/questions |
| --- | --- | --- |
| Coverage | 4.46% (95% CI 1.32–8.13%) | 100.00% (95% CI 100.00–100.00%) |
| Top-one match among answers | 71.43% (95% CI 33.33–100.00%) | 19.75% (95% CI 13.66–26.18%) |
| Top-three match among answers | 71.43% (95% CI 33.33–100.00%) | 25.48% (95% CI 18.40–32.69%) |
| Top-three outcome-key miss / all cases | 1.27% (95% CI 0.00–3.33%) | 74.52% (95% CI 67.31–81.60%) |
| Questions per case | 1.46 (95% CI 1.35–1.57) | 1.46 (95% CI 1.35–1.57) |
| Abstention rate | 95.54% (95% CI 91.87–98.68%) | 0.00% (95% CI 0.00–0.00%) |

Abstention-off answers 157 cases: 31 top-one and 40 top-three matches. It changes only the terminal answer gate; it uses the same simulated questions and posterior as the selected policy. This explains the coverage trade-off without attributing the change to different questioning.

The policy's answered top-one/top-three accuracy intervals use **999 valid draws out of 1,000**: one resample had no answered cases and cannot define answered accuracy. Every other main interval uses 1,000 valid draws. Report the 33.33–100% interval alongside 5/7; seven answers provide weak precision. Named-top ECE over all terminal cases is **0.18364 (95% CI 0.13114–0.24616)**. This does not justify probability wording; bars remain relative support.

## Controls and strata

All three attribute pools, three question strategies, budgets zero through three, all part-change strata and both time-availability strata are retained. All 72 stopping tables passed independent point-metric verification and complete interval replay. The following compact table reports the frozen stopping rule; exact intervals are in the retained JSON.

| Pool | Strategy | Answers / 157 | Top-one matches | Mean questions |
| --- | --- | --- | --- | --- |
| all_attributes | information_gain | 7 | 5 | 1.4586 |
| all_attributes | random | 1 | 1 | 0.1338 |
| all_attributes | no_questions | 0 | 0 | 0.0000 |
| structured_fields_only | information_gain | 7 | 5 | 1.4586 |
| structured_fields_only | random | 2 | 2 | 0.2675 |
| structured_fields_only | no_questions | 0 | 0 | 0.0000 |
| coded_fields_only | information_gain | 0 | 0 | 0.2548 |
| coded_fields_only | random | 0 | 0 | 0.0446 |
| coded_fields_only | no_questions | 0 | 0 | 0.0000 |

The all-attribute and structured-field policies produced the same aggregate stopping measurements in this test. Coded-only information gain answered no cases; answered accuracy is undefined. Preserve that control rather than omit it.

| All-attribute IG stratum | Cases | Answers | Top-one / top-three matches |
| --- | --- | --- | --- |
| named_to_named | 94 | 2 | 0 / 0 |
| same | 51 | 5 | 5 / 5 |
| unknown_to_named | 12 | 0 | 0 / 0 |

All 157 query submissions are after the predeclared latest selection-label cutoff (2 January 2025); therefore the primary and post-selection-label sensitivity results are identical. The cutoff was declared before accessing this archive. Across the combined 2023–2025 corpus, pair construction discarded 12 links with a missing referenced ID, two with an empty/mismatched tail and one nonforward submission; these are corpus-wide counts, not 2025-only exclusions. No eligible pair was excluded for an unknown correction outcome.

At fixed question budget two, all-attribute IG top-one accuracy is 21.02% versus random 12.10%; the paired difference is **8.92 percentage points (95% CI 3.07–14.67)**. At budget three, IG top-one is 18.47%, down from budget two; do not claim that more questions always improve accuracy. These budget curves do not replace the frozen stopping-policy result.

## Error analysis and implications

The initial top ten omitted the recorded part in **113/157 (71.97%)** cases. Reweighting a fixed set of named candidates cannot create a missing part. Both answered misses were in the named-to-named stratum and had no true-part candidate:

| Case | Chosen top part | Recorded correction part | Terminal relative support | Questions |
| --- | --- | --- | --- | --- |
| AALA202507229614 → AALA202507299614 | BOTTLE | RESERVOIR | 0.91188 | 1 |
| AALA202509035297 → AALA202509045297 | PUMP | CONNECTOR | 0.87682 | 2 |

All five correct answers were in the same-part stratum; neither changed-part stratum produced a correct answer under the selected rule. The observed high support on the two misses shows why the fit/threshold does not establish safe real-world diagnostic confidence. All saved answer traces, evidence IDs, beliefs, decisions and audit flags are retained for inspection. Original-field simulated answers are not measurements from technicians. The correction key is used only for downstream scoring, and exact name matching is a proxy.

Follow-up retrieval expansion and candidate rejection belong to a separately declared development experiment with retrieval-owner review and a new untouched validation set. Do not change this frozen test, optimize thresholds against it or reinterpret these results as deployment approval. The current FYP result is the measured trade-off: much lower answer coverage, fewer absolute outcome-key misses, and substantial retrieval failures.

## Provenance and upstream-history workaround

The selected-policy SHA-256 remains `8f4657e3e412b82a80f0972ac829642171dc495710e9a349cec82785748fdb76`.
The pre-access protocol SHA-256 is `93ff4fcc4ffc9e64e59ff97da953fed82f2208dda1bf63da0fdad2e7ee2e61a9`.
The results SHA-256 is `0815e2089902105e9c459ffe0afeffc664a1dc2039419ae415070b972b876a12`.

The first attempt [44905292132](https://github.com/umaritics/halite/actions/runs/44905292132) stopped before opening 2025: FAA had appended one 2024 record. A hash-only comparison proved every original row unchanged. The identifier/order manifest restores the exact 66,080-row 2024 snapshot and verifies its original full canonical hash; the downloaded revision is retained separately. The extra ID `2026FA0000953` is excluded from the frozen history. Missing/changed original content still fails closed. Tests and the procedure were refrozen before the successful test access.

The pre-access receipt was written at **2026-11-21 12:53:36.444866 UTC** after verifying the original historical corpus fingerprint. It records source/parameter/procedure hashes and restoration. The 2025 projection canonical hash is `22bff4cbae45371b60dc5bfca2ca8bff2bf27b4da6af4d8cc0ad176b2ca121e7`. The combined corpus has 196,424 records with no invalid, identical-duplicate or ambiguous IDs. The one-shot access label was removed after the run; later pushes cannot automatically rerun this evaluation.

The ranker came from an earlier prototype with prior 2025 POC exposure. This is a newly frozen-configuration temporal benchmark; the project cannot claim no earlier exposure to any 2025 report. Every evidence access still enforces strictly earlier submission time and query-chain exclusion.

## Verification and retained proof

Full CI on the exact source head passed **485 backend tests, 279 frontend tests, Ruff, both builds, fresh Neo4j/PostgreSQL session and maintenance smoke, and production Chromium research/source-highlighting flows**. Coverage: **5,176 / 6,339 = 81.65%**, passing the exact 80% gate with the same six source scopes.

New procedure checks cover temporal and outcome-key isolation, ECE arithmetic, preflight before networking, canonical download metadata, failed-download cleanup, exact history restoration, missing/changed-history rejection and full synthetic export plus independent replay. The actual hosted verifier independently recalculated all stopping point metrics and replayed all saved question/stopping/ECE intervals.

- `backend/investigation/experiments/results/held_out_2025_v1/`: unmodified hosted results, three case-trace files, pre-test receipt and actual verifier report.
- `docs/work/usman/evidence/phase17-held-out/`: raw JUnit/coverage, exact-head full CI and evaluation metadata/logs, browser proof, history-drift diagnosis and retained-file hashes.
- Hosted `frozen-held-out-source-projections` artifact (run 44906082558): compressed official projections, download metadata and original retrieved 2024 revision. Raw source rows are not committed.
- Ordinary full CI now replays the retained results without network source downloads, fits or sweeps.

The research evaluation phase is complete. Publishing the final results/accepted marker, independent human grounding labels, actual model measurements, final report/defense review, owner review/merge and release remain explicit items in the acceptance matrix. No staging write, model call or local heavy computation was used.
