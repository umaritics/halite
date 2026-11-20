# Managed question snapshots and explicit activation

Status: implemented behind disabled-by-default flag; operating-point selection pending
Date: 2026-11-20
Owners: Usman; shared responsive-shell review Shahmeer

## Context

Offline expected gain is insufficient for durable user answers. Counts, graph
records or policy files may change between asking and answering. Attribute/value
alone also cannot identify a replaced question that happens to use the same field.

## Decision

Require an explicit policy file to activate managed questions. The bundled
integration fixture is labelled experimental; it is not silently deployed as a
chosen operating point. Preserve all stateless compatibility behavior.

Give each question an ID and require it on answers. Save the fixed hypothesis
basis, matrices, codebook, policy, original evidence and prior/posterior. Answer
without graph/model reads and commit via the existing revision CAS transaction.
Use one strict submission-time view for initial ranking and likelihood counts.
Never impute missing/naive timestamps. Persist budget and answers across messages.

## Consequences

Tests cover both SQL engines, concurrency, closure, rollback and application
restart. Built-browser proof uses actual Neo4j/PostgreSQL and a fallback LLM.
2024 selection/2025 holdout and sentence grounding remain distinct requirements.

Visual inspection found the old 256px shared sidebar unusable at phone width;
no-overflow alone was too weak a check. The concrete App/Sidebar patch was prepared
without editing shared files. The user explicitly authorized “Prepare and test
the separate layout branch”. Apply on that separate review branch; Shahmeer review
and merge remain pending, without extending the change into broader shell work.
