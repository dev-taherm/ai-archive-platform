from __future__ import annotations

import logging
from typing import Any

from core.application.interfaces.services import ChatResult, EmbeddingProvider, LLMProvider

logger = logging.getLogger(__name__)


class StubLLMProvider(LLMProvider):
    """Stub LLM provider that returns mock responses when no real provider is configured."""

    def classify(
        self,
        text: str,
        *,
        categories: list[str],
        system_prompt: str | None = None,
    ) -> tuple[str, float]:
        logger.warning("Using stub LLM provider - classify returns mock result")
        return ("unknown", 0.0)

    def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        logger.warning("Using stub LLM provider - extract returns empty dict")
        return {field: "" for field in fields}

    def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        logger.warning("Using stub LLM provider - summarize returns placeholder")
        return f"[Summary requires LLM provider configuration. Text length: {len(text)} chars]"

    def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult:
        logger.warning("Using stub LLM provider - chat returns placeholder")
        return ChatResult(
            content="Chat functionality requires LLM provider configuration. Please set OPENAI_API_KEY or GOOGLE_API_KEY.",
            finish_reason="stop",
        )


class StubEmbeddingProvider(EmbeddingProvider):
    """Stub embedding provider that returns mock embeddings when no real provider is configured."""

    @property
    def dimension(self) -> int:
        return 384

    def embed_text(self, text: str) -> list[float]:
        logger.warning("Using stub embedding provider - returns zero vector")
        return [0.0] * self.dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        logger.warning("Using stub embedding provider - returns zero vectors")
        return [[0.0] * self.dimension for _ in texts]


