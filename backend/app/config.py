from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HomeGuide AI"
    debug: bool = True
    database_url: str = "sqlite:///./data/realestate.db"
    checkpoint_db_url: str = "sqlite:///./data/checkpoints.db"

    google_api_key: str | None = None
    llm_model: str = "gemini-3.1-flash-lite-preview"
    llm_temperature: float = 0.7
    embedding_model: str = "models/text-embedding-004"

    @property
    def llm_configured(self) -> bool:
        return bool(self.google_api_key)

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def semantic_search_enabled(self) -> bool:
        return self.llm_configured


@lru_cache
def get_settings() -> Settings:
    return Settings()
