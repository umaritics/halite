# Diagnostic copilot evidence — 2026-10-17

Branch: `feat/mid1/diagnostic-copilot` from `origin/main` at `223726b`.

## Empty-response finding

The blank-success path was reproduced with a fake live model returning valid
JSON whose `explanation` is empty. Before this change the route accepted that
value and emitted HTTP 200 with empty explanation/evidence/citations. The
regression now expects HTTP 503 with explicit `empty explanation` detail.

The wrapper also previously returned `message.content` without checking for
`None` or whitespace. It now rejects empty content. GPT-OSS completion requests
use a larger output budget, low reasoning effort, and `include_reasoning:false`.
The default model is consistently `openai/gpt-oss-20b` in `config.py`,
`groq_service.py`, and `.env.example`.

This establishes the application-level cause of the blank success: unchecked
empty model content. It does **not** prove why staging's upstream model returned
empty content. Reasoning-budget exhaustion remains plausible but unverified
because the captured staging run lacks response usage/finish-reason logs.

## Automated verification

Focused backend copilot suite:

```text
collected 9 items
test_second_turn_reranks_accumulated_case_and_reports_delta PASSED
test_ruled_out_component_is_not_recommended PASSED
test_invalid_citation_is_flagged_and_never_verified PASSED
test_superseded_record_is_marked_but_not_used_in_ranked_recommendations PASSED
test_validation_unknown_asset_and_model_failure_states PASSED
test_fleet_only_mode_and_deterministic_record_report_selection PASSED
test_period_and_topic_report_selects_only_matching_asset_records PASSED
test_diagnose_empty_explanation_regression_is_explicit_503 PASSED
test_groq_wrapper_rejects_none_content_with_finish_reason PASSED
```

Full backend suite executed every test successfully but the Windows process did
not exit after test teardown and the command harness stopped it after 180 s:

```text
........................................................................ [ 44%]
..............................s.s.s.s.s.s.s.s.s.s.s..s.s.s.s.s.s.s.s.s.. [ 88%]
..................                                                       [100%]
command timed out after 180238 milliseconds
```

Focused frontend diagnostics tests:

```text
✓ src/test/Diagnostics.test.jsx (29 tests)
✓ src/test/DiagnosticsCopilot.test.jsx (4 tests)
Test Files  2 passed (2)
Tests       33 passed (33)
```

Complete frontend suite after restoring all mutation changes:

```text
Test Files  12 passed (12)
Tests       117 passed (117)
Duration    6.17s
```

Production build:

```text
vite v5.4.21 building for production...
✓ 851 modules transformed.
✓ built in 4.82s
```

## Mutation checks

Three temporary mutations were applied one at a time and immediately reverted:

1. Renamed `All fleet` to `Fleet-wide` → the default-filter test failed.
2. Suppressed the `new` ranking movement → the multi-turn movement test failed.
3. Removed `#record_id` from evidence navigation → the deep-link test failed.

Each targeted Vitest command exited 1 with exactly the expected assertion.

## Live verification blockers (not claimed)

The required real local three-turn 813SK run, fleet-wide run, and record summary
were not executed:

```text
GROQ_API_KEY absent from process environment
backend/.env does not exist
Error response from daemon: Docker Desktop is unable to start
DockerDesktop/Wsl/ExecError ... exit status 0xc00000fd
```

No live local JSON is presented. The post-merge staging checks are also pending:
this branch has not yet merged/deployed, so current staging cannot verify the
new route or deployed SHA. Per runtime-honesty rules, live behavior is not
claimed until `/api/health` reports `graph_mode=neo4j`, `llm_mode=live`, a
loaded maintenance corpus, and the expected deployed SHA.
