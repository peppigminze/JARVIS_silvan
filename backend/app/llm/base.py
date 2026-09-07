from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, TypedDict


class ChatMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMUnavailableError(Exception):
    """Raised when the configured LLM backend cannot be reached."""


class LLMProvider(ABC):
    """
    Abstraction over any chat-completion backend.

    V1 ships LocalLLMProvider only. The interface is deliberately
    provider-agnostic so OpenAIProvider / AnthropicProvider / etc. can
    be added later without touching the Agent Core.
    """

    @abstractmethod
    async def chat(self, messages: List[ChatMessage], temperature: float = 0.3) -> str:
        """Send a list of chat messages, return the assistant's reply text.

        Raises LLMUnavailableError if the backend cannot be reached.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the backend is reachable right now."""
        raise NotImplementedError
