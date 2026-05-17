"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. All values come from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: Literal["local", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Database (placeholder, Fase 2)
    database_url: str = "postgresql+psycopg://placeholder"

    # R2 (placeholder, Fase 4)
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""

    # Anthropic (placeholder, Fase 8)
    anthropic_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Import this, not Settings directly."""
    return Settings()
