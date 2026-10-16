# Halite Agent Context Benchmark

## Goal

Measure whether an IDE coding agent explores less of a project when it starts with a Halite-exported context file instead of discovering the architecture from source files alone.

This benchmark supports two tracks:

- IDE-agent proxy metrics
- exact token counting with the local Gemini harness

Proxy metrics:

- files read
- lines loaded from files
- search operations
- agent turns
- elapsed runtime
- answer quality

## Benchmark target

Use the nested `demo-app/` repository as the controlled target.

Relevant files:

- `src/auth/auth.service.ts`
- `src/api/gateway.ts`
- `src/db/postgres.ts`

## Setup

1. In Halite, use **Settings → Export agent context (.md)**.
2. Save the downloaded file unchanged.
3. Open the `demo-app/` project for the IDE agent benchmark.
4. Run each task twice:
   - **Cold run**: give the agent only the task.
   - **Context run**: attach or paste the exported Halite markdown first, then give the same task.

Keep the repo and task text identical between both runs.

## Rules for the benchmark

- Do not let the agent modify code.
- Ask for explanation / review / targeted-change planning tasks only.
- Reset the chat/session between runs.
- Use the same model and tool permissions for both runs.
- For the context run, instruct the agent to verify only the minimum files needed.

## Tasks

### Task 1: Auth validation workflow

Prompt:

> Explain where access-token validation happens, why that logic lives there instead of at the API gateway entry point, and which files you verified.

Expected focus:

- `src/auth/auth.service.ts`
- optional verification of `src/api/gateway.ts`

### Task 2: Invalidation target

Prompt:

> If a commit changes the authentication workflow, which file path should invalidate the stored JWT decision first, and why is that the highest-signal file?

Expected focus:

- `src/auth/auth.service.ts`

### Task 3: Dependency reasoning

Prompt:

> Explain why auth depends on the database layer in this demo and whether changing the query boundary should affect the JWT decision or only implementation details.

Expected focus:

- `src/auth/auth.service.ts`
- `src/db/postgres.ts`

### Task 4: Minimal verification set

Prompt:

> You need to review a proposed refresh-token change. Identify the minimum files that must be inspected before approving it, and justify each one.

Expected focus:

- `src/auth/auth.service.ts`
- maybe `src/api/gateway.ts`
- maybe `src/db/postgres.ts`

### Task 5: Change impact

Prompt:

> A teammate wants to move preprocessing from request time to cache-fill time. Explain how you would verify whether that matches the current workflow design, and list only the files worth opening first.

Expected focus:

- whichever files the exported context says own that workflow
- the key observation is whether the agent keeps file reads narrow

## Exact-token harness

Use `benchmarks/gemini_agent_harness.py` when you want exact API token counts while still reading the local project files.

Example:

```bash
set GEMINI_API_KEY=your_key_here
python benchmarks/gemini_agent_harness.py ^
  --repo demo-app ^
  --tasks benchmarks/tasks_demo_app.json ^
  --context-url https://dev1.corp.curatech.pk/halite-api/api/graph/export/context ^
  --output benchmarks/output/gemini_agent_benchmark.csv
```

The harness:

- reads the local repo
- gives Gemini only the files it asks for
- logs `prompt_tokens`, `completion_tokens`, and `total_tokens`
- also records the same proxy metrics as the IDE benchmark

Use `docs/agent_context_exact_token_results_template.csv` as the reporting shape.

## Proxy metrics worksheet

For each run, capture:

- `files_read_count`
- `total_lines_read`
- `search_count`
- `agent_turns`
- `elapsed_seconds`
- `answer_quality` (`correct`, `partial`, `incorrect`)
- `notes`

If the IDE transcript exposes exact file reads, use that. Otherwise estimate from the visible tool transcript conservatively.

## Scoring guidance

### Correct

- identifies the right file(s)
- explains the workflow/logic correctly
- does not invent unrelated architecture

### Partial

- mostly correct but misses one important file or rationale

### Incorrect

- wrong file focus
- wrong workflow explanation
- relies on guessed facts not present in code/context

## Success criterion

Halite is helping if the context run:

- reads fewer files
- loads fewer lines
- takes fewer turns
- finishes faster
- while preserving equal or better answer quality

## Reporting

Use:

- `docs/agent_context_benchmark_results_template.csv` for the IDE-agent proxy benchmark
- `docs/agent_context_exact_token_results_template.csv` for the exact-token Gemini benchmark

Then compute:

- average reduction in files read
- average reduction in lines loaded
- average reduction in turns
- average reduction in elapsed time
- quality parity or improvement
