# Agent Context Benchmark Summary

## Setup

- Project benchmarked: `demo-app`
- Date: 2026-08-18
- Halite context export: `docs/halite-agent-context-2026-08-18.md`
- IDE agent: Cursor (Task 4 only)
- Exact-token agents:
  - Gemini 2.5 Flash (Task 4 only; later 429 rate-limited)
  - Groq `openai/gpt-oss-20b` (all 5 tasks)

## Numbers to show a supervisor

### Cleanest paired result: Gemini Task 4

Same model, same task, both runs submitted a correct answer.

| Metric | Cold | With Halite | Reduction |
|---|---:|---:|---:|
| Total tokens | 7839 | 3897 | **50.3%** |
| Files read | 2 | 1 | 50% |
| Tool calls | 3 | 1 | 67% |
| Agent turns | 4 | 2 | 50% |
| Quality | Correct | Correct | Same |

### Groq completed pairs (Tasks 2 and 5)

Both modes submitted an answer.

| Task | Cold tokens | Halite tokens | Reduction | Quality |
|---|---:|---:|---:|---|
| 2 Invalidation target | 10652 | 6966 | **34.6%** | Both correct |
| 5 Change impact | 28352 | 21000 | **25.9%** | Both plausible |

Average token reduction on completed Groq pairs: **30.3%**.

### Groq quality wins where cold never finished

| Task | Cold | With Halite |
|---|---|---|
| 1 Auth validation | 23046 tokens, no answer | 9746 tokens, **correct** (−57.7%) |
| 4 Refresh-token review | 24917 tokens, no answer | 25339 tokens, **correct** |

Context did not always reduce tokens here, but it turned two failed cold runs into finished correct answers.

### Negative result (must disclose)

Task 3 (auth vs database dependency): both modes hit the 12-turn limit with no answer. With-context used **more** tokens (23991 → 36032). Do not average this into a savings claim.

## Groq full table

| Task | Cold tokens | Halite tokens | Files cold → Halite | Searches cold → Halite | Turns cold → Halite | Finished? |
|---|---:|---:|---|---|---|---|
| 1 | 23046 | 9746 | 3 → 2 | 8 → 0 | 12 → 6 | Cold no / Halite yes |
| 2 | 10652 | 6966 | 1 → 1 | 3 → 0 | 6 → 3 | Yes / yes |
| 3 | 23991 | 36032 | 2 → 3 | 9 → 8 | 12 → 12 | No / no |
| 4 | 24917 | 25339 | 2 → 3 | 9 → 4 | 12 → 9 | Cold no / Halite yes |
| 5 | 28352 | 21000 | 4 → 3 | 4 → 6 | 12 → 11 | Yes / yes |

## Cursor IDE proxy (Task 4)

| Metric | Cold | With Halite |
|---|---:|---:|
| Files read | 3 | 4 |
| Searches | 1 | 0 |
| Agent turns | 4 | 3 |
| Quality | Correct | Correct, with line citations |

## How to talk about this

Halite does not shrink the first prompt. It shrinks the **agent loop**: fewer searches, fewer extra files, fewer turns, so later prompts stop replaying exploration.

Best claim with evidence:

> On a controlled demo repo, attaching Halite context cut Gemini token use by 50% on a refresh-token review task with the same correct answer. On Groq, completed paired tasks averaged a 30% token cut, and Halite produced a correct answer on two tasks where the cold agent never finished.

Do not claim a 50% saving across all five Groq tasks. Task 3 failed in both modes, and incomplete 12-turn loops inflate token counts.

## Files

- Groq raw output: `benchmarks/output/groq_full_benchmark.csv`
- Exact-token sheet: `docs/agent_context_exact_token_results.csv`
- Cursor Task 4: `docs/agent_context_benchmark_results.csv`
