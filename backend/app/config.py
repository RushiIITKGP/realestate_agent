from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HomeGuide AI"
    debug: bool = True
    database_url: str = "sqlite:///./data/realestate.db"
    checkpoint_db_url: str = "sqlite:///./data/checkpoints.db"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
