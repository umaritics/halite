# Cursor Agent Benchmark Prompts

Use these prompts in a fresh IDE-agent session against `demo-app/`.

Run each task twice:

1. **Cold run**
2. **With Halite context**

## Shared rules

Paste these rules before every task:

> Do not modify code.  
> Answer the question by inspecting only the minimum necessary files.  
> At the end, list:
> 1. files you opened
> 2. searches you performed
> 3. whether you are fully confident, partially confident, or uncertain

## Context run preface

For the context-assisted run, paste this before the task:

> You are given a Halite project-memory export for this repository.  
> Use it as your starting context.  
> Verify only the minimum necessary files before answering.  
> Do not rescan the repository broadly unless the context is insufficient.

Then attach or paste the exported markdown file.

## Tasks

### Task 1

> Explain where access-token validation happens, why that logic lives there instead of at the API gateway entry point, and which files you verified.

### Task 2

> If a commit changes the authentication workflow, which file path should invalidate the stored JWT decision first, and why is that the highest-signal file?

### Task 3

> Explain why auth depends on the database layer in this demo and whether changing the query boundary should affect the JWT decision or only implementation details.

### Task 4

> You need to review a proposed refresh-token change. Identify the minimum files that must be inspected before approving it, and justify each one.

### Task 5

> A teammate wants to move preprocessing from request time to cache-fill time. Explain how you would verify whether that matches the current workflow design, and list only the files worth opening first.
