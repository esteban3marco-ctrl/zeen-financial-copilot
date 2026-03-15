"""Application configuration via Pydantic Settings v2."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # OPA
    OPA_URL: str = "http://localhost:8181"

    # Demo
    DEMO_MODE: bool = True

    # LLM
    LLM_MODEL: str = "claude-sonnet-4-5"

    # E2B
    E2B_API_KEY: str = ""

    # OpenTelemetry
    OPENTELEMETRY_ENDPOINT: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
