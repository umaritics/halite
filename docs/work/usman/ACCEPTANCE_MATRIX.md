# Usman FYP I final acceptance matrix

Source: master plan and `docs/plan/AGENT_GUIDE_USMAN.md`. This matrix retains the
whole objective and distinguishes a verified backend slice from a finished product.
A local pass is not a merge, deployment, cross-review or empirical research result.

| Package / deliverable | Current authoritative evidence | State and remaining acceptance |
| --- | --- | --- |
| WP-S0 backend preparation | Phase 1 commit `51196fd`, structural proof, PR #27 | Extension points verified; legacy retirement and cross-review/merge remain |
| WP-S11 lint/coverage | CI workflow, Ruff config/dev dependency; phase 2 lint and coverage outputs | Local and GitHub lint/JUnit/coverage reports verified on `4764581`; NFR-04 target still not met for the broad legacy-inclusive scope |
| Form 10 | `docs/fyp1-final/PANEL_ACTION_REGISTER.md` | Template/evidence register provided; actual Mid-I feedback and supervisor confirmation still required |
| WP-S1 adapter / degraded / cache | Adapter and degraded tests; phase 1/2 results; production session smoke | Backend and feature UI verified; quick diagnosis sends `allow_degraded=true` |
| WP-S2 sessions | Three tables; lifecycle/access/replay tests on SQLite and PostgreSQL; local production-startup smoke | Backend verified locally and by GitHub CI on `4764581` |
| WP-S3 history/workspace/logout | 246 frontend tests and real-browser feature preview | Server-backed package verified; shared production-shell integration authorized for a separate review branch |
| WP-S4 ranker port / beliefs / policy / fitting / abstention | Session API explicitly reports `policy_status=not_configured` | Not implemented; no calibrated beliefs or measured operating point claimed |
| WP-S5 attributes / information gain / simulation / coded fields | No new question logic claimed | Not implemented; official code meanings, data/backfill/reviewer and measured experiments required |
| WP-S6 sentence grounding L2/L3 | Diagnose now enforces the bounded prompt allow-list; Copilot already enforces context IDs | L2 added; sentence checker and frontend marks still required |
| WP-S7 home dashboard | Authenticated summary extension points; sessions summary now live and scoped | Home package and partial/all failure tests verified; production-shell integration next |
| WP-S8 model judge / labels / grounding evaluation | No results claimed | Tooling, actual human labels, judge run, precision/recall/kappa and baseline remain |
| WP-S9 printable report | Escaped authenticated closed-session HTML endpoint and integration test | Backend and print layout verified (1280px and A4 width); one-click feature action verified with real browser; production-shell integration next |
| WP-S10 model comparison | No results claimed | Build/run 20-prompt harness; actual M4 measurements and owner decision remain |
| Report / diagrams / disclosure / defense | Engineering knowledge and AI-assistance log updated | Student-owned report review, final traceability/diagrams, disclosure and genuine defense/rehearsal evidence remain |
| Integration/release | Draft PRs #27/#28, both verified by GitHub CI on their implementation commits; staging unchanged | Cross-review, accepted shared contracts, merged green CI, deploy and full UI/runtime verification remain |

Next execution: finish the session/CI review slice, then frontend integration and
pure decision/question/grounding packages with leakage-safe evaluation. Never mark
the full goal complete while any required cell above remains unverified.
