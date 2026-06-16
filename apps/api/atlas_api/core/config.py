from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ATLAS_",
        extra="ignore",
    )

    app_name: str = "atlas-api"
    environment: str = Field(default="development", alias="ATLAS_ENV")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://atlas:atlas@localhost:5432/atlas"
    redis_url: str = "redis://localhost:6379/0"
    storage_path: str = "atlas.local.sqlite3"
    artifact_dir: str = "artifacts"
    cors_origins: list[str] = ["http://localhost:3000"]
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    log_level: str = "INFO"
    embedding_dimensions: int = 1536

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
