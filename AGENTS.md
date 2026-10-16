# AGENTS.md — Halite (all coding agents)

This file is the **universal entrypoint** for any AI coding agent or human contributor (Cursor, Claude Code, Copilot, Codex, chat agents, etc.). Cursor rules under `.cursor/rules/` reinforce the same protocol; **this file is the portable contract**.

## Before you change anything

1. Read [`knowledge/README.md`](knowledge/README.md) (router).
2. Open the linked **context** + **flow** for the area you will touch.
3. Check [`knowledge/decisions/INDEX.md`](knowledge/decisions/INDEX.md) for constraints.
4. Respect Mid-I ownership (do not edit another owner’s files without a handoff decision):
   - **Umar** — graph schema/queries, diagnose/chat internals, ranking, citations, diagnostic tests
   - **Usman** — ingest, conflict engine, maintenance APIs, Compose, CI, `main.py` wiring
   - **Shahmeer** — React UX, `frontend/src/api/client.js`, Vitest

## After you change behavior or contracts

You **must** update the knowledge bank in the same change set:

| What changed | Update |
| --- | --- |
| Module behavior / design | matching `knowledge/context/**` note |
| End-to-end path or file deps | matching `knowledge/flows/FLOW-*.md` (keep Mermaid graph accurate) |
| Non-obvious choice | new `knowledge/decisions/DEC-YYYYMMDD-slug.md` + index row |
| Primary files / owners | `knowledge/REGISTRY.md` and/or `knowledge/INDEX.md` |
| Deferred / out-of-scope | `knowledge/context/01_domain_scope_deferred.md` |

Do not leave the bank stale. Code + knowledge bank ship together.

## Source-of-truth order

1. Working code + executed tests  
2. Mid-I assessment / university rubric  
3. `docs/Halite_FYP_Report.pdf`, `docs/halite_timeline.pdf`, `docs/halite_work_division_mid1.pdf`  
4. `knowledge/**` (durable engineering memory)  
5. `docs/mid1/**` (dated audit evidence)  
6. `docs/obsolete/**` — **historical only; never current requirements**

## Knowledge bank layout

```text
knowledge/
  README.md       # router — start here for task routing
  INDEX.md        # keyword / path lookup
  REGISTRY.md     # modules ↔ code ↔ owners
  context/        # semantic + human rationale
  decisions/      # short ADRs (DEC-*)
  flows/          # intended flows + dependency graphs
```

## Official Mid-I PDFs

- `docs/halite_work_division_mid1.pdf`
- `docs/Halite_FYP_Report.pdf`
- `docs/halite_timeline.pdf`

## Runtime honesty

Never claim live Neo4j or live LLM without `/api/health` agreeing (`graph_mode`, `llm_mode`, `maintenance_corpus_loaded`). Prefer failing loudly over inventing records or citations.

## Shared staging backend (team default)

- Public API: `https://dev1.corp.curatech.pk/halite-api`
- Partner guide: [`knowledge/context/modules/remote_backend.md`](knowledge/context/modules/remote_backend.md)
- Frontend should use `VITE_API_URL=https://dev1.corp.curatech.pk/halite-api/api` in `.env.local`
- Backend deploys via GitHub Actions (`deploy-staging.yml`); do not assume local `:8000` is staging
- Logs without SSH: `GET /api/ops/logs` + `X-Ops-Token`, or Actions workflow **Fetch staging backend logs**
