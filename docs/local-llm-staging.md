# Local LLM on staging (Ollama, Docker-internal only)

Halite’s conflict engine needs many small **JSON classifications**. Groq’s free **tokens-per-day** cap blocks full-corpus backfill (~2,079 records). Staging runs **Ollama** on the shared VM with **no public port** so only the `halite-api` container can call it.

**Related:** [`security-public-deployment.md`](security-public-deployment.md), [`knowledge/decisions/DEC-20261115-local-ollama-staging.md`](../knowledge/decisions/DEC-20261115-local-ollama-staging.md), [`docs/mid1/25_local_llm_staging_evidence.md`](mid1/25_local_llm_staging_evidence.md), [`DEC-20261116-staging-corpus-analysis-complete`](../knowledge/decisions/DEC-20261116-staging-corpus-analysis-complete.md).

---

## Model choice (2026-11-15)

| Model (Ollama tag) | Role | RAM (loaded, CPU Q4) | Notes |
| --- | --- | --- | --- |
| **`phi4-mini`** (default on staging) | Conflict classification | ~2.5–3.5 GiB | Reddit / Ollama threads: reliable **structured JSON** without Qwen3 “thinking” token waste |
| `qwen3:4b` | Alternate | ~3.1–3.5 GiB | Newer line; on OpenAI-compat API Qwen3 may emit thinking unless `reasoning_effort: none` |
| `qwen3:1.7b` | Minimal RAM | ~2.2 GiB | Fastest on 4 GiB hosts; weaker on nuanced aviation prose |
| `qwen2.5:3b-instruct` | Previous recommendation | ~2.5–3.2 GiB | Superseded on staging by `qwen3:4b` for quality at same RAM class |

We did **not** expose Ollama to the internet; quality can be validated offline on the 141-pair ground-truth set before trusting auto-accept rates.

---

## Security architecture

```text
Internet → Caddy :443 → 127.0.0.1:8002 → halite-api (HALITE_API_KEY / JWT)
                              │
                              └── Docker bridge `halite_app` only
                                        halite-api ──Bearer OLLAMA_API_KEY──► halite-ollama:11434
                                        (no host port published)
```

| Control | Implementation |
| --- | --- |
| **No WAN access to Ollama** | `docker-compose.vm.yml` `ollama` service has **no `ports:`** mapping |
| **API key on Ollama** | `OLLAMA_API_KEY` on the Ollama container; `OPENAI_COMPAT_API_KEY` in `backend/.env` (same value) |
| **Caller authorization** | End users never hit Ollama; only authenticated Halite `/api/*` routes invoke the LLM adapter |
| **Resource caps** | `mem_limit: 4g`, `cpus: 2`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_KEEP_ALIVE=5m` |
| **Blast radius** | Compromise of Halite API still cannot open Ollama to the internet without host Docker changes |
| **Secrets** | `OLLAMA_API_KEY` in `/home/umar/halite/.env` and `backend/.env`; `chmod 600`; never committed |

**Do not** add a Caddy `handle` for `:11434`, bind Ollama to `0.0.0.0` on the host, or run `ollama serve` on the host outside Docker without the same network isolation.

---

## Environment variables

### Repo root `.env` (next to `docker-compose.vm.yml`)

| Variable | Purpose |
| --- | --- |
| `OLLAMA_API_KEY` | Passed into `halite-ollama`; must match backend `OPENAI_COMPAT_API_KEY` |

Generate:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### `backend/.env` (staging)

```dotenv
LLM_PROVIDER=openai_compatible
OPENAI_COMPAT_BASE_URL=http://halite-ollama:11434/v1
OPENAI_COMPAT_API_KEY=<same as OLLAMA_API_KEY>
GROQ_MODEL=phi4-mini
MAINT_ANALYSIS_MODE=cascade
```

Keep `GROQ_API_KEY` unset or leave in place as fallback only if you switch `LLM_PROVIDER` back to `groq`.

`/api/health` reports `llm_provider`, `llm_mode`, and `model`.

---

## Operator runbook

### First-time model pull (on the VM)

```bash
cd /home/umar/halite
docker compose -f docker-compose.vm.yml up -d ollama
docker exec halite-ollama ollama pull phi4-mini
docker compose -f docker-compose.vm.yml up -d --build api
```

### Smoke test (from API container — proves internal DNS + API key)

```bash
docker exec halite-api python -c "
from config import settings
from services.groq_service import GroqService
svc = GroqService(
    settings.OPENAI_COMPAT_API_KEY,
    settings.llm_model,
    demo_mode=False,
    provider='openai_compatible',
    openai_compat_base_url=settings.OPENAI_COMPAT_BASE_URL,
)
print(svc.extract_json('Say hello in JSON: {\"ok\": true}', max_tokens=32))
"
```

### Verify nothing listens on 11434 on the host

```bash
ss -tlnp | grep 11434 || echo 'OK: no host listener'
```

### Conflict backfill

Use existing ops flow: `POST /api/maintenance/analysis/run` with `X-Ops-Token` (and auth gate), or CLI `backfill` with live stack. Prefer **`MAINT_ANALYSIS_MODE=cascade`** to reduce model calls.

---

## Swap space (recommended)

The VM has **no swap**. Before long CPU inference runs:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

Add `/swapfile` to `/etc/fstab` if the host policy allows.

---

## Rollback to Groq

1. Set `LLM_PROVIDER=groq` and `GROQ_API_KEY` in `backend/.env`.
2. `docker compose -f docker-compose.vm.yml up -d api` (Ollama may stay stopped).
3. Confirm `/api/health` shows `llm_provider=groq` and `llm_mode=live`.

---

## File map

| File | Role |
| --- | --- |
| `docker-compose.vm.yml` | `halite-ollama` service + internal network |
| `backend/services/groq_service.py` | `openai_compatible` HTTP adapter |
| `backend/config.py` | `LLM_PROVIDER`, `OPENAI_COMPAT_*` |
| `docs/security-public-deployment.md` | Layer 1–5 threat model (LLM is layer 6, private) |