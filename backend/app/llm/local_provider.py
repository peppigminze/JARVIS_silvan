from __future__ import annotations

import logging
from typing import List

import httpx

from app.llm.base import ChatMessage, LLMProvider, LLMUnavailableError

logger = logging.getLogger("jarvis.llm.local")


class LocalLLMProvider(LLMProvider):
    """
    Talks to a local, OpenAI-compatible chat completion endpoint.

    This works out of the box with Ollama (>= 0.1.x), which exposes
    POST {base_url}/v1/chat/completions, as well as any other local
    runtime that implements the same contract (e.g. LM Studio,
    llama.cpp server in OpenAI-compat mode).

    No API key is required or sent.
    """

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def chat(self, messages: List[ChatMessage], temperature: float = 0.3) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError as exc:
            logger.error("Local LLM connection failed: %s", exc)
            raise LLMUnavailableError("Local LLM is unavailable.") from exc
        except httpx.TimeoutException as exc:
            logger.error("Local LLM request timed out: %s", exc)
            raise LLMUnavailableError("Local LLM is unavailable.") from exc
        except httpx.HTTPStatusError as exc:
            logger.error("Local LLM returned an error status: %s", exc)
            raise LLMUnavailableError("Local LLM is unavailable.") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected local LLM response shape: %s", data)
            raise LLMUnavailableError("Local LLM returned an unexpected response.") from exc

    async def health_check(self) -> bool:
        url = f"{self.base_url}/v1/models"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                return resp.status_code < 500
        except httpx.HTTPError:
            return False
