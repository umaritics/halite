# Usman FYP I final acceptance matrix

Source: master plan and `docs/plan/AGENT_GUIDE_USMAN.md`. This matrix retains the
whole objective and distinguishes a verified backend slice from a finished product.
A local pass is not a merge, deployment, cross-review or empirical research result.

| Package / deliverable | Current authoritative evidence | State and remaining acceptance |
| --- | --- | --- |
| WP-S0 backend preparation | Phase 1 commit `51196fd`, structural proof, PR #27 | Extension points verified; legacy/dependency cleanup and cross-review/merge remain |
| WP-S11 lint/coverage | CI workflow, Ruff config/dev dependency; phase 2 lint and coverage outputs | Local and GitHub lint/JUnit/coverage reports verified on `4764581`; NFR-04 target still not met for the broad legacy-inclusive scope |
| Form 10 | `docs/fyp1-final/PANEL_ACTION_REGISTER.md` | Template/evidence register provided; actual Mid-I feedback and supervisor confirmation still required |
| WP-S1 adapter / degraded / cache | Adapter and degraded tests; phase 1/2 results; production session smoke | Backend and feature UI verified; quick diagnosis sends `allow_degraded=true` |
| WP-S2 sessions | Three tables; lifecycle/access/replay tests on SQLite and PostgreSQL; local production-startup smoke | Backend verified locally and by GitHub CI on `4764581` |
| WP-S3 history/workspace/logout | 246 frontend tests and real-browser feature preview | Server-backed package verified; shared production-shell integration verified on separate review branch; owner review/merge pending |
| WP-S4 ranker port / beliefs / policy / fitting / abstention | Pure core/ranker port; 321 backend tests; stored belief/entropy replay; real 406-pair 2023 fit and 389-pair 2024 selection, versioned results | Core and pre-question selection verified; runtime remains uncalibrated/unconfigured; question-conditioned selection, operating-point choice, final plots/panels and 2025 evaluation remain |
| WP-S5 attributes / information gain / simulation / coded fields | 342 backend tests; official FAA source; 389-pair 2024 three-control experiment, exact replay and figure | Pure/offline core and separate ingest/backfill review preparation and managed runtime verified (384 backend tests; 264 frontend tests; phone/desktop integration verified); managed answer handling and built-browser flow verified behind explicit flag; selected operating point, owner review/merge and actual staging backfill remain |
| WP-S6 sentence grounding L2/L3 | Saved-evidence sentence checker, frozen 2023 part guards, optional encoder port, durable session/quick diagnosis audits and frontend marks | Implemented; default unrated and experimental/selected configuration explicit; human calibration/threshold acceptance and source-token highlighting remain |
| WP-S7 home dashboard | Authenticated summary extension points; sessions summary now live and scoped | Home package and partial/all failure tests verified; production-shell integration verified on review branch; owner review/merge pending |
| WP-S8 model judge / labels / grounding evaluation | Frozen 150-pair constructed FAA-text packet, blinded Usman/Umar review copies, strict CSV import/agreement/adjudication and separate 99/51 threshold fit/validation tools | Tooling verified with synthetic tests only; actual independent labels, adjudication, human metrics, generated-answer validation, L4 and no-evidence comparison remain |
| WP-S9 printable report | Escaped authenticated closed-session HTML endpoint and integration test | Backend and print layout verified (1280px and A4 width); one-click feature action verified with real browser; production-shell integration verified on review branch; owner review/merge pending |
| WP-S10 model comparison | Frozen twenty-real-case packet, portable standard-library runner, raw journals/resume and generated comparison table | PR #37; user requested self-contained runner for M4 execution; Eleven focused tests, isolated-Python HTTP/resume/error smoke and deterministic ZIP verified; actual M4 model measurements and Usman decision remain |
| Research result product panel | Committed 2024 results, scientific plots and checksum-validated authenticated experiments endpoint; local publication tests passed | Endpoint hosted integration checks, “How Halite decides” charts, chosen-point marker after acceptance, shared chart integration and UI verification remain |
| Report / diagrams / disclosure / defense | Explicitly authorized AI-assisted design draft; engineering knowledge and disclosure log | Student-owned report review, final traceability/diagrams, disclosure and genuine defense/rehearsal evidence remain |
| Integration/release | Draft PRs #27–#35 passed hosted checks; grounding/review preparation PR #36 also passed all hosted checks; staging unchanged | Cross-review, accepted shared contracts, merged green CI, deploy and full UI/runtime verification remain |

Next execution: complete comparison tooling/CI, research-result product display,
question-conditioned selection, accepted operating point and held-out evaluation. Never mark
the full goal complete while any required cell above remains unverified.
