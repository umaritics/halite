# Portable measured comparison before interactive-model selection

- **Status:** implemented / measurement and selection pending
- **Owners:** Usman; M4 execution with Shahmeer
- **Date:** 2026-11-20

## Context

The master plan requires a 20-prompt comparison and a readable decision table.
No accessible M4 endpoint was supplied. The user explicitly chose: finish and
verify a self-contained runner that Shahmeer can execute on the M4.

## Decision

Ship a standard-library-only portable runner and frozen real selection-case
packet, with native Ollama HTTP, exact provider identities, serial timing, raw
journals, explicit errors, strict resume and a generated comparison table. Use
ten extraction/ten prose prompts plus ten paired no-evidence prose calls. Declare
this comparison prompt version rather than falsely claiming live-prompt replay.
Keep temporal/correction-chain isolation and held-out 2025 untouched.

Require actual runner hardware for the M4 role, while explicitly distinguishing
runner identity from inference-server placement. Do not call synthetic transport
verification a real-model or M4 result. Do not choose a model automatically or
invent calibrated sentence ratings to fill missing metrics.

## Consequences

The comparison tooling can be verified and handed off without a new app
dependency, model download or staging change. Actual M4 measurements, calibrated
grounding metrics and Usman's model decision remain separate acceptance gates.
Provider failures and invalid outputs remain inspectable rather than hidden.
