---
id: mod-backend-foundation
title: Backend vertical extension points
status: active
owners: [Usman]
updated: 2026-11-20
---

# Backend foundation

The compatible foundation implements master-plan WP-S0 steps 2–5. Legacy
retirement remains separate because existing maintenance/domain and security
contracts explicitly consume it. See DEC-20261120-backend-foundation.

## Graph access

`graph.queries` re-exports the exact `GraphRepository` class from `graph.repo`.
`graph.memory_store` re-exports `MemoryGraphStore` from `graph.memory`. Both
packages use `core`, `retrieval`, `integrity` and isolated `legacy` mixins.

- Core: lifecycle, low-level node/edge helpers, asset/record CRUD and shared
  asset history/pagination. Usman stewards these shared methods.
- Retrieval: recent history, batches by ID, record listing, graph overview and
  neighborhood. Umar owns query evolution.
- Integrity: supersession links, correction lists, analysis state and partial
  record updates. Shahmeer owns query evolution.
- Legacy: existing software behavior and seeding, preserved until its retirement
  contract is resolved. No new product functionality belongs here.

The split changes neither method signatures nor bodies. Facades preserve
existing application, test and script imports. Mixins call shared methods
through `self`; no dynamic method installation or monkey-patching is used.

## Relational model discovery

`db/models/identity.py` contains the unchanged five identity tables and Base.
The package re-exports existing public names and imports `evaluation`, `integrity`
and `sessions` extension modules once. New tables added there are discovered by
the existing `Base.metadata.create_all`; no existing column is migrated.

## HTTP and configuration

Authenticated GET summaries are registered once in `api/router.py` at
`/api/{retrieval,evaluation,integrity,sessions}/summary`. Each returns title,
link and an empty stats list. No placeholder count is represented as live data.
Vertical owners replace empty statistics with measured values later.

Marked RETRIEVAL_, INTEGRITY_, SESSION_ blocks exist in `config.py` and
`backend/.env.example`. `RETRIEVAL_MODE` defaults to `mid_heuristic`; the setting
reserves the contract and does not itself change retrieval behavior.

## Model output formats

`GroqService.chat` and `chat_with_usage` default to `json_mode=False`.
Both `extract_json` methods explicitly use `json_mode=True`. Quick-diagnose JSON
explanations and Copilot fact extraction also explicitly request JSON; Copilot
and maintenance-chat prose keep the default. The format passes
through local-compatible HTTP calls, Groq SDK calls and the fallback-key retry.
Prose requests omit `response_format`; JSON requests send `json_object`.
Provider failures still raise, empty responses are still rejected, usage
accounting remains intact, and no canned maintenance answer is introduced.

## Verification

Unchanged existing tests plus `test_backend_preparation.py` and
`test_model_adapter_format.py`; phase evidence in `docs/work/usman/WORK_LOG.md`.

## Remaining retirement and dependency cleanup

The independent dependency branch removes unused direct requirements without
changing route/domain behavior. Actual CSV/document consumers are retained and
hosted reports verify resolution. See DEC-20261121-dependency-cleanup.

The concrete legacy retirement proposal is in
`docs/work/usman/LEGACY_RETIREMENT_HANDOFF.md` and its exact two-file integration
patch. The user authorized preparing/testing it on a separate review branch on
21 November; runtime retirement and owner review are not claimed by this branch.
