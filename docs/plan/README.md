# Halite plan files

These are the agent-facing files of the Halite Master Plan, written on 20 November 2026 against
`origin/main` at `ac5aa66`. The human-facing plan (state of the project, handbook criteria, ownership,
timeline, demo script) is the shared document "Halite Master Plan: ownership, CCPs and timeline".

| File | Who reads it | What it holds |
| --- | --- | --- |
| [`CONTRACTS.md`](CONTRACTS.md) | Every agent, at the start of every session | Ownership by file, the preparation pull requests, interfaces, naming, corpus files, evaluation discipline, verified facts about the code |
| [`AGENT_GUIDE_UMAR.md`](AGENT_GUIDE_UMAR.md) | Umar's agent | V1 Retrieval and Ranking |
| [`AGENT_GUIDE_SHAHMEER.md`](AGENT_GUIDE_SHAHMEER.md) | Shahmeer's agent | V2 Record Integrity, plus the frontend preparation |
| [`AGENT_GUIDE_USMAN.md`](AGENT_GUIDE_USMAN.md) | Usman's agent | V3 Investigation Sessions, plus the backend preparation and CI |

## How to start an agent session

Say this, then name one work package:

> Read `AGENTS.md`, then `docs/plan/CONTRACTS.md`, then `docs/plan/AGENT_GUIDE_<NAME>.md`.
> Work only on work package `<ID>`. Stop and ask me at every point the guide marks.

## Adopting the plan

1. All three owners read the master plan and agree to it.
2. Commit these files to `main`.
3. In the same commit, add `knowledge/decisions/DEC-20261120-vertical-ownership.md` and replace the
   mid-term ownership list in `AGENTS.md` and `knowledge/context/02_ownership_mid1.md` with the three verticals.
   The handbook requires ownership changes to be recorded when they happen.
4. Tag that commit. The December work starts from it.

## Keeping the files true

- A guide that disagrees with the code is a defect. Fix the guide in the same pull request as the code.
- Line numbers refer to `ac5aa66`. After the preparation pull requests move files, update the paths here.
- Numbers about the FAA data were measured on the raw yearly files on 20 November 2026. The corpus builder's
  de-duplicated counts replace them once it has run.
