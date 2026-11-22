# Usman FYP I final acceptance matrix

Source: master plan and `docs/plan/AGENT_GUIDE_USMAN.md`. This matrix retains the
whole objective and distinguishes a verified backend slice from a finished product.
A local pass is not a merge, deployment, cross-review or empirical research result.

| Package / deliverable | Current authoritative evidence | State and remaining acceptance |
| --- | --- | --- |
| WP-S0 backend preparation | Phase 1 commit `51196fd`, structural proof, PR #27 | Extension points and full software/dependency retirement verified (PR #42/#43; source 5817fd9). Merged via PR #27/#48; independent owner cross-review remains |
| WP-S11 lint/coverage | CI workflow, Ruff config/dev dependency; phase 2 lint and coverage outputs | Verified on `2af4d97` / run 44909092445: 499 backend tests; 5,264/6,433 = 81.83% with the exact 80% gate passed and unchanged six source scopes. Merged via PR #48/#49; actual Form 10 confirmation remains a separate gate |
| Form 10 | `docs/fyp1-final/PANEL_ACTION_REGISTER.md` | Usman confirmed on 2026-11-22 that Mid-I had no comments or modification requests; exact statement recorded. Official-form transfer and any required supervisor confirmation/signature are not claimed |
| WP-S1 adapter / degraded / cache | Adapter and degraded tests; phase 1/2 results; production session smoke | Backend and feature UI verified; quick diagnosis sends `allow_degraded=true` |
| WP-S2 sessions | Three tables; lifecycle/access/replay tests on SQLite and PostgreSQL; local production-startup smoke | Backend verified locally and by GitHub CI on `4764581` |
| WP-S3 history/workspace/logout | 246 frontend tests and real-browser feature preview | Server-backed package verified; shared production-shell integration verified on separate review branch; integrated through PR #48; independent owner review pending |
| WP-S4 ranker port / beliefs / policy / fitting / abstention | Pure core/ranker port; 321 backend tests; stored belief/entropy replay; real 406-pair 2023 fit and 389-pair 2024 selection, versioned results | Core, pre-question/product charts and joint stopping selection verified (4,536 rows, 389 pairs/340 originals, 1,000 clustered draws; independent metric replay). Runtime remains unconfigured; Usman accepted .80/.50; frozen-policy preflight is hosted verified. 2025 fixed evaluation verified on 5a5060b / run 44906082558: 157 pairs/140 originals, 72 tables and all interval replay; 7 answers, 5 matches, no tuning |
| WP-S5 attributes / information gain / simulation / coded fields | 342 backend tests; official FAA source; 389-pair 2024 three-control experiment, exact replay and figure | Pure/offline core and separate ingest/backfill review preparation and managed runtime verified (384 backend tests; 264 frontend tests; phone/desktop integration verified); managed answer handling and built-browser flow verified behind explicit flag; joint stopping selection now verified; Usman accepted .80/.50; integrated through PR #48; independent owner review and actual staging backfill remain |
| WP-S6 sentence grounding L2/L3 | Saved-evidence sentence checker, frozen 2023 part guards, optional encoder port, durable session/quick diagnosis audits and frontend marks | Implemented; source-word hover/focus and exact replay verified on `4136fc3` (449 backend / 279 frontend tests, real browser, dark/light phone screenshots); default unrated and experimental/selected configuration explicit; human calibration/threshold acceptance remain |
| WP-S7 home dashboard | Authenticated summary extension points; sessions summary now live and scoped | Home package and partial/all failure tests verified; production-shell integration verified on review branch; integrated through PR #48; independent owner review pending |
| WP-S8 model judge / labels / grounding evaluation | Frozen 150-pair constructed FAA-text packet, blinded Usman/Umar review copies, strict CSV import/agreement/adjudication and separate 99/51 threshold fit/validation tools | Blinded-label tools verified; explicit offline L4 instrument hosted verified on 8d3abab / run 44982604273 (515 backend / 283 frontend; 82.09%) and merged via PR #51. Actual independent labels, adjudication, human metrics, generated-answer validation, model-judge measurements/live integration and no-evidence comparison remain |
| WP-S9 printable report | Escaped authenticated closed-session HTML endpoint and real signed-in public browser44994441004 | Merged PR56, main CI/deploy passed on6c3cd0d; actual closed-case replay/one-click A4 PDF verified. All4pages visually reviewed;20/20 full saved narratives retained;16mm margins. Independent owner review remains separate |
| WP-S10 model comparison | Frozen twenty-real-case packet, portable runner, raw journals and readable actual comparison table | Portable M4 harness verified as requested. Real staging run44984568357 retained all30attempts:24responses,6evidence-prose timeouts at180s; independent replay verified the negative result (STAGING_REFERENCE_RESULTS.md). Separate600s deadline and failure-postflight fix merged via PR54; new full measurement not yet run; actual M4 measurements and Usman model decision remain separate |
| Research result product panel | PRs #38–#40; `ecdc264`, hosted run 44856875802; 445 backend / 275 frontend tests; real production-browser and retained screenshot proof | Implemented and verified: endpoint, controls, 95% intervals, both themes at 1280/390px, artifact parity and error/empty/retry. Accepted joint-selection marker and frozen2025publication verified on2af4d97/run44909092445 (499backend/283frontend tests,81.83%, real container/browser, all phone charts). Merged through PR #48; independent shared-file owner review remains |
| Report / diagrams / disclosure / defense | AI-assisted Markdown chapter, editable `USMAN_INVESTIGATION_CHAPTER.docx` and matching PDF, architecture/defense companion, design note and disclosure log | Full chapter, references and three frozen-result figures prepared; eleven rendered Word/PDF pages visually verified, two native equations, exact table parity and accessibility audit passed. See EDITABLE_REPORT_VERIFICATION.md. Student review, final team formatting and genuine defense/rehearsal evidence remain |
| Integration/release | PR #27/#48/#49 merged; dependent #28–#47 proven ancestors and closed as integrated. Exact-source CI 44911995235: 500 backend / 283 frontend, 81.83%; merged-main CI 44912401813 passed | Frontend publicly delivered; corrected backend deployment 44912646403 passed; public health/version confirmed exact 29f4f59, Neo4j/live phi4-mini/PostgreSQL and 2,079 records. Independent owner cross-review, actual staging coded-field backfill and authenticated public product acceptance remain |

Next execution: user-authorized merge/integration alongside remaining
human/model/report/review/release work. Final product publication is verified. Joint selection, user numeric
choice, pre-test freeze and actual 2025 evaluation are verified. Retain all human/review/release gates. Exact backend coverage
acceptance is now verified; this does not complete the remaining research or release. Never mark
the full goal complete while any required cell above remains unverified.

The user confirmed that Usman and Muhammad Umar will complete the two independent
grounding reviews. No completed labels or derived human metrics have been received.

Latest public acceptance supersedes the old release-row snapshot: PR55/56
merged and deployed, latest6c3cd0d; source CI549backend tests,82.60% measured
coverage, frontend/full-stack passed. Public auth/research/home/populated history/
closed replay/print/phone/logout verified44994441004. Actual live session prose
and quick explanation still timed out; do not claim runtime model acceptance.
