from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    GITEA_BASE_URL: str = ""
    GITEA_TOKEN: str = ""
    GITEA_WEBHOOK_SECRET: str = ""

    SECRET_KEY: str = "halite-dev-secret"
    FRONTEND_URL: str = "http://localhost:5173"

    DEMO_MODE: bool = True
    MAX_UPLOAD_MB: int = 10

    # Maintenance domain settings
    MAINT_CONFIDENCE_THRESHOLD: float = 0.72  # Provisional — pending T7 calibration
    MAINT_DATA_DIR: str = "data"              # Base data directory (raw/ and processed/ beneath)
    MAINT_MAX_CANDIDATES: int = 25            # Max prior records to consider per conflict check

    @property
    def neo4j_configured(self) -> bool:
        return bool(self.NEO4J_URI and self.NEO4J_PASSWORD)

    @property
    def groq_configured(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def gitea_configured(self) -> bool:
        return bool(self.GITEA_BASE_URL and self.GITEA_TOKEN)


settings = Settings()
