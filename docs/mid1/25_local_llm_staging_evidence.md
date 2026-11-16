# Local LLM staging evidence — 2026-11-15 / 2026-11-16

Related decisions: `DEC-20261115-local-ollama-staging`,
`DEC-20261116-staging-corpus-analysis-complete`. Runbook: `docs/local-llm-staging.md`.

## Infra

| Check | Result |
| --- | --- |
| Ollama host port | No `11434` listener on VM WAN/host |
| Swap | 4 GiB `/swapfile` active |
| Staging model | `phi4-mini` via `LLM_PROVIDER=openai_compatible` |
| Analysis mode | `MAINT_ANALYSIS_MODE=cascade` |
| Budget caps (VM) | `MAINT_DAILY_REQUEST_LIMIT=100000`, `MAINT_DAILY_TOKEN_LIMIT=50000000` |

## Smoke (in-container)

```json
{"label": "no_conflict", "rationale": "smoke test"}
```

## Ground-truth benchmark (FAA supplemental citations, n=15)

Command:

```bash
docker exec halite-api python scripts/benchmark_local_llm_gt.py \
  --from-graph-supplemental --limit 15 --passes 1
```

Summary (`docs/mid1/logs/local_llm_gt_benchmark_2026-11-15.json`):

| Metric | Value |
| --- | --- |
| pairs_scored | 15/15 |
| parse_failures | 0 |
| positive_label_rate | 0.8667 |
| label_histogram | partial_supersedes 7, supersedes 6, no_conflict 2 |

This is a **smoke** on supplemental-citation pairs, not held-out F1.

## Full-corpus backfill (staging Neo4j)

| When (UTC) | Event |
| --- | --- |
| 2026-11-15 15:27+ | Restarted `scripts/vm/run_analysis_backfill.sh` after `remaining_unscored` fix |
| 2026-11-16 04:16:07 | `corpus fully scored`; job exited |

**Final coverage (Neo4j / last log payload):**

| analysis_state | count |
| --- | ---: |
| unscored | 0 |
| scored | 1,585 |
| needs_review | 494 |
| reviewed | 0 |
| **total** | **2,079** |

**By method (stored on records):** screen 1,043; llm 801; llm-escalated 235.

Logs: `/home/umar/halite/logs/analysis_backfill.log` on the VM.

## Operator checks

```bash
curl -s https://dev1.corp.curatech.pk/halite-api/api/health   # llm_mode, model
# authenticated / ops:
# GET /api/maintenance/analysis/status
# GET /api/maintenance/review-queue
```

## Git / CD

Pushed to `origin/main`: local Ollama adapter + compose (`86ae117`, `63720a6`).
Redeploy staging so `/api/ops/version` `git_sha` matches `main` after CI.