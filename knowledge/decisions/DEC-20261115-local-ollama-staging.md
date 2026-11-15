---
id: dec-local-ollama-staging
title: Private Ollama on staging for unbounded conflict classification
status: accepted
owners: [Umar, Usman]
updated: 2026-11-15
---

# DEC-20261115 — Local Ollama on staging (Docker-internal)

## Context

After the shared-VM cryptominer incident (exposed Gitea), the team hardened Halite per `DEC-20261114-public-api-security-hardening`. Conflict confidence backfill remains blocked by Groq free-tier **TPD** (~200k), with ~1,976 records still `unscored` after partial runs (`docs/mid1/19_confidence_and_corrections_evidence.md`).

The VM has ~7.6 GiB RAM, four vCPUs, no GPU, and no swap. A **4 GiB** cgroup for inference is acceptable if Ollama is not reachable from the public internet.

## Decision

1. Add **`halite-ollama`** to `docker-compose.vm.yml` with **no published ports**, `OLLAMA_API_KEY`, CPU/RAM limits, and model volume `halite_ollama_data`.
2. Configure staging **`LLM_PROVIDER=openai_compatible`** with `OPENAI_COMPAT_BASE_URL=http://halite-ollama:11434/v1` and matching API key (extends `GroqService` via httpx, not a second public route).
3. Default staging model tag **`phi4-mini`** (Reddit/Ollama structured-output threads; avoids Qwen3 thinking overhead on the OpenAI-compat path). Alternates: `qwen2.5:3b-instruct`, `qwen3:4b` with `reasoning_effort: none`.
4. Enable **`MAINT_ANALYSIS_MODE=cascade`** on staging to cut model-eligible pairs before tuning quality.
5. Document operator steps in `docs/local-llm-staging.md`.

## Consequences

- End users and the website **never** call Ollama directly; only authenticated Halite API routes do.
- Quality of local 4B models may increase `needs_review` vs Groq 20B/120B; ground-truth eval remains required before demo claims.
- CD must deploy the Ollama service; first deploy requires a one-time `ollama pull` on the VM.
- Groq remains the default for **local dev** (`LLM_PROVIDER=groq`).

## Owners

Umar (VM security posture), Usman (Compose + LLM adapter wiring).