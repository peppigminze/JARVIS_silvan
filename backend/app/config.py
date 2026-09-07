"""
Central configuration for the JARVIS backend.

All values are loaded from environment variables / a .env file.
NOTHING here is hardcoded as a secret default that would be safe to
ship - the *.env.example* file documents which variables must be set.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./jarvis.db"

    # LLM
    LLM_PROVIDER: str = "local"
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "llama3.1:8b"
    LOCAL_LLM_TIMEOUT_SECONDS: float = 60.0

    # API server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Auth
    USER_TOKEN: str = "change-me-user-token"
    AGENT_TOKEN: str = "change-me-agent-token"

    # Local PC Agent (agent/run_agent.py) - shares this same .env file.
    BACKEND_BASE_URL: str = "http://localhost:8000"
    AGENT_POLL_INTERVAL_SECONDS: float = 5.0
    AGENT_HEARTBEAT_INTERVAL_SECONDS: float = 15.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so the .env file is only parsed once."""
    return Settings()
