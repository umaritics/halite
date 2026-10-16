---
id: flows-index
title: Flows index
status: active
owners: [all]
updated: 2026-10-16
---

# Flows index

| ID | Flow | Primary owners |
| --- | --- | --- |
| FLOW-diagnose | Symptom → ranked checks + citations | Umar + Shahmeer |
| FLOW-conflict-review | Record conflict → review queue → accept/reject | Usman + Shahmeer |
| FLOW-ingest | FAA CSV → Neo4j assets/records | Usman |
| FLOW-ci | Push/PR → GitHub Actions gates | Usman |
| FLOW-deploy | Shared VM staging deploy + remote logs | Umar, Usman |

Each flow doc includes: happy path, failure modes, and a Mermaid dependency graph across files/modules.
