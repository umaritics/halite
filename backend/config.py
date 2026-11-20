from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    GROQ_API_KEY: str = ""
    GROQ_API_KEY_FALLBACK: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # LLM backend: groq (cloud) or openai_compatible (e.g. Ollama on Docker internal DNS).
    # Staging may use openai_compatible so conflict analysis is not capped by Groq TPD.
    LLM_PROVIDER: str = "groq"
    OPENAI_COMPAT_BASE_URL: str = ""
    OPENAI_COMPAT_API_KEY: str = ""
    LLM_REQUEST_TIMEOUT_S: float = 120.0

    # Deprecated: self-hosted Gitea was retired after the Nov 2026 VM incident.
    # Routes fail closed (410 Gone) unless ENABLE_GITEA_INTEGRATION=true.
    ENABLE_GITEA_INTEGRATION: bool = False
    GITEA_BASE_URL: str = ""
    GITEA_TOKEN: str = ""
    GITEA_WEBHOOK_SECRET: str = ""

    SECRET_KEY: str = "halite-dev-secret"
    JWT_SECRET_KEY: str = ""
    JWT_ACCESS_TTL_MINUTES: int = 15
    JWT_REFRESH_TTL_DAYS: int = 7
    AUTH_MAX_FAILED_ATTEMPTS: int = 5
    AUTH_LOCKOUT_MINUTES: int = 15

    # Relational database for Workspace Identity, RBAC, Sessions & Audit Trail
    # Production/Compose: postgresql://halite:<password>@postgres:5432/halite (or Supabase Postgres URI)
    # Empty in DEMO_MODE=true uses an isolated in-memory SQLite database for deterministic tests.
    DATABASE_URL: str = ""

    # Optional idempotent startup bootstrap for the initial organization admin (never commit credentials)
    BOOTSTRAP_ORG_NAME: str = "Halite Maintenance Operations"
    BOOTSTRAP_ORG_SLUG: str = "halite-ops"
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
    BOOTSTRAP_ADMIN_NAME: str = "Halite Administrator"

    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = ""
    CORS_ORIGIN_REGEX: str = r"^https://halite(?:-[a-z0-9-]+)?\.vercel\.app$"

    DEMO_MODE: bool = True
    MAX_UPLOAD_MB: int = 10

    # Application-layer API authentication & public surface controls
    # Required whenever DEMO_MODE=false (fail-closed 503 if unset).
    HALITE_API_KEY: str = ""
    # None -> enabled in DEMO_MODE=true, disabled (404) when DEMO_MODE=false
    EXPOSE_OPENAPI: bool | None = None

    # In-process sliding-window rate limits (per client IP)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_API_PER_MINUTE: int = 180
    RATE_LIMIT_LLM_PER_MINUTE: int = 20
    RATE_LIMIT_AUTH_FAILURES_PER_MINUTE: int = 20

    # Privileged operator secret (partners/ops use X-Ops-Token; never commit real value)
    OPS_TOKEN: str = ""
    GIT_SHA: str = "unknown"
    DEPLOYED_AT: str = ""

    # Maintenance domain settings
    MAINT_CONFIDENCE_THRESHOLD: float = 0.50  # Re-calibrated via evaluate_conflict_detection.py
    MAINT_DATA_DIR: str = "data"              # Base data directory (raw/ and processed/ beneath)
    MAINT_MAX_CANDIDATES: int = 25            # Max prior records to consider per conflict check
    MAINT_ANALYSIS_MODE: str = "legacy"        # legacy remains the safe default; cascade is opt-in
    MAINT_DAILY_REQUEST_LIMIT: int = 1000
    MAINT_DAILY_TOKEN_LIMIT: int = 200000
    MAINT_BUDGET_UTILIZATION: float = 0.90
    MAINT_BUDGET_TOKEN_RESERVE: int = 1000
    MAINT_BUDGET_STATE_FILE: str = ""          # defaults to MAINT_DATA_DIR/analysis_budget.json

    # --- RETRIEVAL_ ---
    RETRIEVAL_MODE: str = "mid_heuristic"

    # --- INTEGRITY_ ---
    # Reserved for the integrity owner's additive settings.

    # --- SESSION_ ---
    SESSION_QUESTIONS_ENABLED: bool = False
    # Explicit reviewable operating-point file; enabling without it fails closed.
    SESSION_POLICY_FILE: str = ""
    SESSION_GROUNDING_FILE: str = ""  # No guessed thresholds or implicit whitelist.

    @property
    def neo4j_configured(self) -> bool:
        return bool(self.NEO4J_URI and self.NEO4J_PASSWORD)

    @property
    def llm_model(self) -> str:
        if self.LLM_PROVIDER == "openai_compatible":
            return (self.GROQ_MODEL or "phi4-mini").strip()
        return self.GROQ_MODEL

    @property
    def llm_configured(self) -> bool:
        if (self.LLM_PROVIDER or "groq").strip().lower() == "openai_compatible":
            return bool(
                (self.OPENAI_COMPAT_BASE_URL or "").strip()
                and (self.OPENAI_COMPAT_API_KEY or "").strip()
            )
        return bool(self.GROQ_API_KEY)

    @property
    def groq_configured(self) -> bool:
        """Backward-compatible alias used by /api/health and startup logs."""
        return self.llm_configured

    @property
    def gitea_configured(self) -> bool:
        """Deprecated: Gitea integration is disabled unless ENABLE_GITEA_INTEGRATION=true."""
        return bool(
            self.ENABLE_GITEA_INTEGRATION and self.GITEA_BASE_URL and self.GITEA_TOKEN
        )

    @property
    def api_key_configured(self) -> bool:
        return bool((self.HALITE_API_KEY or "").strip())

    @property
    def api_auth_required(self) -> bool:
        """Fail closed whenever DEMO_MODE is false, or whenever HALITE_API_KEY is configured."""
        return self.api_key_configured or not self.DEMO_MODE

    @property
    def effective_jwt_secret(self) -> str:
        return (self.JWT_SECRET_KEY or self.SECRET_KEY or "").strip()

    @property
    def jwt_secret_strong(self) -> bool:
        secret = self.effective_jwt_secret
        return (
            len(secret) >= 32
            and secret not in {"halite-dev-secret", "change-me-in-production"}
        )

    @property
    def database_configured(self) -> bool:
        return bool((self.DATABASE_URL or "").strip())

    @property
    def openapi_enabled(self) -> bool:
        if self.EXPOSE_OPENAPI is not None:
            return bool(self.EXPOSE_OPENAPI)
        return bool(self.DEMO_MODE)

    @property
    def cors_origins_list(self) -> list[str]:
        raw = [
            self.FRONTEND_URL,
            *(item.strip() for item in (self.CORS_ALLOWED_ORIGINS or "").split(",")),
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        seen: set[str] = set()
        origins: list[str] = []
        for origin in raw:
            cleaned = (origin or "").strip().rstrip("/")
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                origins.append(cleaned)
        return origins


settings = Settings()
