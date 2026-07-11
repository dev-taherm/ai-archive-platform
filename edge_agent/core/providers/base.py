from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ParserProvider(ABC):
    """Subclasses should set `provider_name` for plugin registration."""

    provider_name: str = ""

    @abstractmethod
    def parse(self, file_path: str) -> Any:
        ...


class OCRProvider(ABC):
    """Subclasses should set `provider_name` for plugin registration."""

    provider_name: str = ""

    @abstractmethod
    def extract_text(
        self, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        ...


class LLMProvider(ABC):
    """Subclasses should set `provider_name` for plugin registration."""

    provider_name: str = ""

    @abstractmethod
    def extract_entities(
        self, text: str, schema: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        ...


class EmbeddingProvider(ABC):
    """Subclasses should set `provider_name` for plugin registration."""

    provider_name: str = ""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...
