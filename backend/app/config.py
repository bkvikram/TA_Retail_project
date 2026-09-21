from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable via environment variables (12-factor)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Retail Pricing Feed Service"
    database_url: str = "postgresql+asyncpg://retail:retail@localhost:5432/retail_pricing"
    api_key: str = "dev-local-api-key"  # replaced by OAuth2/JWT + IdP in production, see docs/ARCHITECTURE.md
    max_upload_mb: int = 200
    csv_batch_size: int = 2000
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
