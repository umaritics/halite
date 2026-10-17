# Conflict-analysis cost cascade evidence — 2026-10-17

Scope: offline implementation and proof only. `MAINT_ANALYSIS_MODE` still
defaults to `legacy`. No full analysis, live-model smoke call, staging write,
or held-out-year evaluation was performed in this round.

## Pre-registration and ownership

The threshold and design were recorded before held-out inspection in
`knowledge/decisions/DEC-20261017-analysis-cost-cascade.md`. That decision also
records the team lead’s cross-owner waiver for this bounded change. The screen
does not use same-day, and removes both boilerplate and the explicit
`SUPPLEMENTAL REPORT FOR <ID>` answer key.

## Real-corpus offline measurement

Command (in-memory graph; real local corpus; zero model calls):

```text
cd backend
python scripts/measure_analysis_cost.py --corpus <local>/backend/data/processed/sdr_poc_corpus.csv --ground-truth <local>/backend/data/processed/ground_truth_pairs.csv
```

Relevant output, pasted from the run:

```json
{
  "ingest": {"assets_created": 118, "records_created": 2079},
  "candidate_rule": {
    "histogram_uncapped": {"0": 244, "1": 261, "2": 209, "3-5": 372, "6+": 993},
    "records_with_candidates": 1835,
    "raw_positive_score_pairs": 32457,
    "pairs_after_25_cap": 19119,
    "pairs_sent_per_model_record": 1,
    "self_consistency_requests_per_sent_pair": 5
  },
  "cascade_screen": {
    "dev_threshold_max_retaining_all": 0.7931034482758621,
    "ground_truth_retained": 141,
    "ground_truth_n": 141,
    "old_top1": 124,
    "containment_first_top1": 136,
    "eligible_before_screen": 1835,
    "eligible_after_screen": 1031,
    "screened_free": 804
  },
  "cache": {"entries": 63, "schema_has_votes": false, "schema_has_usage": false}
}
```

The production constant is the conservative rounded threshold `0.79`, which
is below the measured minimum `0.793103...`.

| Offline development measure | Legacy | Cascade |
| --- | ---: | ---: |
| Known true prior remains in candidates | 141/141 | 141/141 |
| Known true prior ranked first | 124/141 (87.9%) | 136/141 (96.5%) |
| Model-eligible records before screen | 1,835 | 1,835 |
| Free deterministic decisions | 0 | 804 (43.8%) |
| Remaining model classifications | 1,835 | 1,031 |

This is development-set retrieval evidence, not classification recall or
held-out quality. The screen clears the required 40% disclosure boundary, but
does not by itself deliver a 10x reduction.

## Request, token, and quota projection

Adaptive voting makes two requests when the initial votes agree and five when
they do not. The high bound deliberately assumes every remaining pair
escalates.

| Mode | Model classifications | Requests | Reduction vs 9,175 | Tokens | Days at 90% of 1,000 RPD |
| --- | ---: | ---: | ---: | --- | ---: |
| Legacy | 1,835 | 9,175 | — | UNVERIFIED | 11 |
| Cascade low (all agree at 2) | 1,031 | 2,062 | 77.5% | UNVERIFIED | 3 |
| Cascade high (all escalate to 5) | 1,031 | 5,155 | 43.8% | UNVERIFIED | 6 |

Token days cannot be projected from the old cache: its 63 entries retain only
the final majority result, not votes or provider usage. The new cache schema
records prompt, completion, reasoning, and total tokens when returned. Round
four must measure the real agreement rate and token distribution. Therefore no
10x token-cost claim is made here.

Groq’s official free-plan table, checked 2026-10-17, lists 30 RPM, 1,000 RPD,
8,000 TPM and 200,000 TPD for both the configured `qwen/qwen3.8-27b` and the
repository-default `openai/gpt-oss-20b`:
https://console.groq.com/docs/rate-limits. The budget defaults match this table
and stop at 90% (900 requests or 180,000 tokens), while the account console
remains authoritative for organization-specific exceptions.

## Persistence, budget, and API behavior

Each new classification records model, method, passes, all votes, vote
agreement, timestamp, and returned token fields in cache and record metadata.
Neo4j stores votes as JSON text because maps cannot be node-property values.
Old flat cache entries normalize to the new response shape. Cache hits return
before budget preflight and therefore do not debit requests or tokens.

The simulated UTC rollover test used a 10-request/1,000-token budget at 90%:

```text
9 requests x 50 tokens -> requests_remaining=0, tokens_remaining=450
next preflight -> BudgetExhausted("daily_request_budget")
2026-10-18T00:01:00Z -> requests_used=0, tokens_used=0
```

The API test also exercised a one-request budget: the first no-candidate row
was persisted, the next classification stopped after its first provider call,
and `POST /analysis/run` returned HTTP 200 with
`stopped_reason="daily_request_budget"`, `processed=1`, and
`budget_remaining.requests_used=1`. `GET /analysis/status` now includes
`by_method`; the batch response separates `model_records`, `screen_records`,
and `no_candidate_records`. The CLI’s `--until-budget` implies resume behavior
and stops cleanly on the same exception.

## Tests and mutation checks

Local backend suite after restoring all temporary mutations:

```text
python -B -m pytest -q -p no:cacheprovider
171 passed, 23 skipped in 8.95s
```

The 23 skips are real-Neo4j tests; CI supplies Neo4j 5 Community. The final CI
result is recorded below after the PR run.

Three temporary mutations were applied individually and reverted:

1. `CASCADE_SCREEN_THRESHOLD` changed from `0.79` to `0.0`: the no-model screen test failed by entering the fake LLM.
2. Initial cascade passes changed from 2 to 1: the two-vote agreement/metering test failed.
3. Request-budget boundary changed from `< 1` to `< 0`: the UTC persistence/rollover test failed because exhaustion was not raised.

Frontend verification:

```text
npm test
Test Files  12 passed (12)
Tests       126 passed (126)

npm run build
✓ 854 modules transformed.
✓ built in 7.27s
```

The build retained the existing large-chunk warning. Frontend tests retained
pre-existing React `act(...)` warnings; neither caused a failure.

## NOT RUN / UNVERIFIED

- Live Groq smoke calls: 0 (deferred to round four as requested).
- Prompt/completion/reasoning-token averages and total token projection.
- Cascade classification recall, precision, F1, and escalation frequency.
- Held-out-year quality.
- Full-corpus analysis and final correction/review counts.
- Shared staging analysis, migration, deployment, or any graph write.
