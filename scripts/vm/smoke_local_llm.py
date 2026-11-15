"""One-shot smoke test for Docker-internal Ollama (run inside halite-api)."""
from config import settings
from services.groq_service import GroqService

svc = GroqService(
    settings.OPENAI_COMPAT_API_KEY,
    settings.llm_model,
    demo_mode=False,
    provider="openai_compatible",
    openai_compat_base_url=settings.OPENAI_COMPAT_BASE_URL,
)
out = svc.extract_json(
    'Return only JSON: {"label": "no_conflict", "rationale": "smoke test"}',
    max_tokens=80,
)
print(out[:200])