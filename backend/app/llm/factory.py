from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.local_provider import LocalLLMProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Returns the configured LLMProvider.

    V1 only implements "local". The branch structure below is where
    future providers (OpenAIProvider, AnthropicProvider, ...) plug in
    based on LLM_PROVIDER, without any change needed in the Agent Core.
    """
    settings = settings or get_settings()

    if settings.LLM_PROVIDER == "local":
        return LocalLLMProvider(
            base_url=settings.LOCAL_LLM_BASE_URL,
            model=settings.LOCAL_LLM_MODEL,
            timeout_seconds=settings.LOCAL_LLM_TIMEOUT_SECONDS,
        )

    # Future:
    # if settings.LLM_PROVIDER == "openai":
    #     return OpenAIProvider(...)
    # if settings.LLM_PROVIDER == "anthropic":
    #     return AnthropicProvider(...)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
        "V1 only supports 'local'."
    )
