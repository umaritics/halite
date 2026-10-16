---
id: knowledge-root
title: Halite Knowledge Bank
status: active
owners: [all]
updated: 2026-10-16
---

# Halite Knowledge Bank

**Read this file first** before any non-trivial change. This bank is the project’s working memory: architecture, decisions, flows, ownership, deferred work, and module dependencies.

Universal agent contract (any tool): [`AGENTS.md`](../AGENTS.md) at the repo root.

## How to use (humans and agents)

1. Open **this README** → follow the router below for your task.
2. Open the linked **context** note for domain knowledge and “why”.
3. Open the linked **flow** for the intended end-to-end path + dependency graph.
4. Scan **decisions/INDEX.md** for ADRs that constrain the change.
5. After you change behavior, **update** the matching context/flow/decision (see `AGENTS.md` and `.cursor/rules/`).

## Source-of-truth hierarchy

| Priority | Source | Use for |
| --- | --- | --- |
| 1 | Working code + executed tests | What is true today |
| 2 | Mid-I assessment / university rubric | What must be shown |
| 3 | `docs/Halite_FYP_Report.pdf`, `docs/halite_timeline.pdf`, `docs/halite_work_division_mid1.pdf` | Product scope, timeline, ownership |
| 4 | This knowledge bank (`knowledge/**`) | Durable engineering memory |
| 5 | `docs/mid1/*` evidence notes | Audit snapshots (may be dated) |
| 6 | `docs/obsolete/*` | Historical only — do not treat as current product |

When sources conflict: prefer code+tests; record a decision note; get team approval for contract changes.

## Router (task → start here)

| If you are working on… | Start with |
| --- | --- |
| Project overview / Mid-I goals | [context/00_project_overview.md](context/00_project_overview.md) |
| Scope, non-goals, deferred features | [context/01_domain_scope_deferred.md](context/01_domain_scope_deferred.md) |
| Ownership / who may edit what | [context/02_ownership_mid1.md](context/02_ownership_mid1.md) |
| System architecture | [context/03_architecture.md](context/03_architecture.md) |
| Graph schema / Neo4j / data | [context/04_data_and_graph.md](context/04_data_and_graph.md) |
| Diagnostics / ranking / citations | [context/modules/diagnostics.md](context/modules/diagnostics.md) + [diagnostics_u1_audit.md](context/modules/diagnostics_u1_audit.md) + [flows/FLOW-diagnose.md](flows/FLOW-diagnose.md) |
| Conflict engine / review queue | [context/modules/conflict_engine.md](context/modules/conflict_engine.md) + [flows/FLOW-conflict-review.md](flows/FLOW-conflict-review.md) |
| Ingestion / corpus | [flows/FLOW-ingest.md](flows/FLOW-ingest.md) |
| Frontend UX | [context/modules/frontend.md](context/modules/frontend.md) |
| CI / Docker / setup | [context/modules/devops.md](context/modules/devops.md) + [flows/FLOW-ci.md](flows/FLOW-ci.md) |
| Shared remote VM backend / CD / logs | [context/modules/remote_backend.md](context/modules/remote_backend.md) + [flows/FLOW-deploy.md](flows/FLOW-deploy.md) |
| Why a past choice was made | [decisions/INDEX.md](decisions/INDEX.md) |
| Keyword / file → doc lookup | [INDEX.md](INDEX.md) |
| Module → code map | [REGISTRY.md](REGISTRY.md) |

## Folder contract

```text
knowledge/
  README.md          ← you are here (router)
  INDEX.md           ← keyword / path index
  REGISTRY.md        ← modules ↔ primary code files
  context/           ← semantic + human rationale knowledge
    modules/         ← per-module deep context
  decisions/         ← short ADRs (DEC-*)
  flows/             ← intended flows + dependency graphs
```

## Writing rules (keep retrieval cheap)

- Prefer **short hub docs** (≤ ~150 lines) with links; put detail in module/flow notes.
- Every decision file: `Status`, `Context`, `Decision`, `Consequences`, `Owners`.
- Every flow file: steps, actors, APIs, **Mermaid dependency graph**, failure modes.
- Frontmatter: `id`, `title`, `status`, `owners`, `updated`, optional `depends_on`.
- Do not duplicate the FYP report verbatim — summarize and link PDFs by path.
- Mid-I evidence logs stay under `docs/mid1/`; summarize lasting lessons here as decisions/context.

## Current branch baseline

- Implementation branch for Umar Mid-I graph/diagnostics work: `umar/mid1-graph-diagnostics` (from `origin/usman` @ `b949de4`; supersedes deleted `feat/mid1/graph-diagnostics`).
- Usman Mid-I DevOps evidence tip (inherited): see `docs/mid1/05_usman_final_audit.md` and [decisions/DEC-20261016-usman-baseline.md](decisions/DEC-20261016-usman-baseline.md).
