"""
Central configuration for the JARVIS backend.

All values are loaded from environment variables / a .env file.
NOTHING here is hardcoded as a secret default that would be safe to
ship - the *.env.example* file documents which variables must be set.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# The .env file lives in the project root (shared with agent/run_agent.py),
# not in backend/, so it must be resolved relative to this file rather than
# to the current working directory of whoever launches uvicorn.
_PROJECT_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV,
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

    # PC control tools (project spec sections 13/16). Comma-separated
    # absolute paths. Empty by default - file/terminal tools refuse to
    # touch anything until the user explicitly opts a directory in.
    ALLOWED_DIRECTORIES: str = ""
    TERMINAL_TIMEOUT_SECONDS: float = 30.0

    # Sync/message retries (project spec section 19). A message that
    # fails because the local LLM was unreachable gets requeued instead
    # of failing permanently, up to this many times, with an increasing
    # backoff so a down Ollama isn't hammered every poll interval.
    MESSAGE_MAX_RETRIES: int = 3
    MESSAGE_RETRY_BACKOFF_SECONDS: float = 15.0

    # Cloud LLM fallback (project spec sections 8/9). LOCAL FIRST,
    # ALWAYS - disabled by default, so JARVIS never makes a paid API
    # call unless the user explicitly opts in here AND supplies their
    # own key. Only used when the local LLM raises LLMUnavailableError;
    # never used just because the cloud model might be "better".
    CLOUD_LLM_ENABLED: bool = False
    CLOUD_LLM_BASE_URL: str = "https://api.openai.com/v1"
    CLOUD_LLM_MODEL: str = "gpt-4o-mini"
    CLOUD_LLM_API_KEY: str = ""
    CLOUD_LLM_TIMEOUT_SECONDS: float = 30.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_directories_list(self) -> List[str]:
        return [d.strip() for d in self.ALLOWED_DIRECTORIES.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so the .env file is only parsed once."""
    return Settings()
