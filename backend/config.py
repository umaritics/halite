from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    GITEA_BASE_URL: str = ""
    GITEA_TOKEN: str = ""
    GITEA_WEBHOOK_SECRET: str = ""

    SECRET_KEY: str = "halite-dev-secret"
    FRONTEND_URL: str = "http://localhost:5173"

    DEMO_MODE: bool = True
    MAX_UPLOAD_MB: int = 10

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
