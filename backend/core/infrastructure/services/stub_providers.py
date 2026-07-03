from __future__ import annotations

import logging
from typing import Any, Sequence

from core.application.interfaces.services import EmbeddingProvider, LLMProvider, OCRProvider, StorageBackend
from core.domain.documents.value_objects import Confidence, Language

logger = logging.getLogger(__name__)


class StubLLMProvider(LLMProvider):
    """Stub LLM provider that returns mock responses when no real provider is configured."""

    async def classify(
        self,
        text: str,
        *,
        categories: list[str],
        system_prompt: str | None = None,
    ) -> tuple[str, float]:
        logger.warning("Using stub LLM provider - classify returns mock result")
        return ("unknown", 0.0)

    async def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        logger.warning("Using stub LLM provider - extract returns empty dict")
        return {field: "" for field in fields}

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        logger.warning("Using stub LLM provider - summarize returns placeholder")
        return f"[Summary requires LLM provider configuration. Text length: {len(text)} chars]"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        logger.warning("Using stub LLM provider - chat returns placeholder")
        return "Chat functionality requires LLM provider configuration. Please set OPENAI_API_KEY or GOOGLE_API_KEY."


class StubEmbeddingProvider(EmbeddingProvider):
    """Stub embedding provider that returns mock embeddings when no real provider is configured."""

    @property
    def dimension(self) -> int:
        return 1536

    async def embed_text(self, text: str) -> list[float]:
        logger.warning("Using stub embedding provider - returns zero vector")
        return [0.0] * self.dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        logger.warning("Using stub embedding provider - returns zero vectors")
        return [[0.0] * self.dimension for _ in texts]


class StubOCRProvider(OCRProvider):
    """Stub OCR provider that returns placeholder text when no real provider is configured."""

    async def extract_text(
        self,
        content: bytes,
        *,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        logger.warning("Using stub OCR provider - extract_text returns placeholder")
        return f"[OCR requires PaddleOCR configuration. Content type: {content_type}]"

    async def detect_language(self, text: str) -> Language:
        logger.warning("Using stub OCR provider - detect_language returns unknown")
        return Language.UNKNOWN

    async def get_confidence(self, text: str) -> Confidence:
        logger.warning("Using stub OCR provider - get_confidence returns 0.0")
        return Confidence(value=0.0)


class StubStorageBackend(StorageBackend):
    """Stub storage backend that stores files in memory for development."""

    def __init__(self) -> None:
        self._storage: dict[str, bytes] = {}

    async def save(
        self,
        content: bytes,
        path: str,
        *,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        self._storage[path] = content
        return path

    async def retrieve(self, path: str) -> bytes:
        return self._storage.get(path, b"")

    async def delete(self, path: str) -> bool:
        if path in self._storage:
            del self._storage[path]
            return True
        return False

    async def list(
        self,
        prefix: str = "",
        *,
        limit: int = 1000,
    ) -> Sequence[str]:
        return [k for k in self._storage if k.startswith(prefix)][:limit]

    async def get_url(self, path: str, *, expires_in: int = 3600) -> str:
        return f"file://{path}"

    async def exists(self, path: str) -> bool:
        return path in self._storage
