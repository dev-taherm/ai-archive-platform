from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Sequence
from uuid import UUID

from core.domain.documents.value_objects import Confidence, Language, DocumentType


class StorageBackend(ABC):
    """Abstract interface for file storage operations."""

    @abstractmethod
    async def save(
        self,
        content: bytes,
        path: str,
        *,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store content at the given path. Returns the storage key."""

    @abstractmethod
    async def retrieve(self, path: str) -> bytes:
        """Retrieve content from storage by path."""

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete content from storage. Returns True if deleted."""

    @abstractmethod
    async def list(
        self,
        prefix: str = "",
        *,
        limit: int = 1000,
    ) -> Sequence[str]:
        """List storage keys matching the prefix."""

    @abstractmethod
    async def get_url(self, path: str, *, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for the given path."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check whether content exists at the given path."""


class OCRProvider(ABC):
    """Abstract interface for OCR text extraction."""

    @abstractmethod
    async def extract_text(
        self,
        content: bytes,
        *,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        """Extract text content from a document or image via OCR."""

    @abstractmethod
    async def detect_language(self, text: str) -> Language:
        """Detect the primary language of the given text."""

    @abstractmethod
    async def get_confidence(self, text: str) -> Confidence:
        """Return the confidence score of the OCR extraction."""


class LLMProvider(ABC):
    """Abstract interface for large language model operations."""

    @abstractmethod
    async def classify(
        self,
        text: str,
        *,
        categories: list[str],
        system_prompt: str | None = None,
    ) -> tuple[str, float]:
        """Classify text into one of the given categories.

        Returns (category, confidence).
        """

    @abstractmethod
    async def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Extract structured data fields from text."""

    @abstractmethod
    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a concise summary of the given text."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Have a conversational exchange with the LLM."""


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding generation."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Implementations may batch requests for efficiency.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""


class FileScanner(ABC):
    """Abstract interface for filesystem scanning and watching."""

    @abstractmethod
    async def scan_folder(
        self,
        path: str,
        *,
        recursive: bool = True,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Scan a folder and yield file metadata for each discovered file."""

    @abstractmethod
    async def watch_folder(
        self,
        path: str,
        *,
        recursive: bool = True,
        callback: Any | None = None,
    ) -> None:
        """Begin watching a folder for changes.

        Calls the callback with (event_type, path) tuples when files change.
        """

    @abstractmethod
    async def stop_watching(self, path: str) -> None:
        """Stop watching a folder for changes."""

    @abstractmethod
    def is_watching(self, path: str) -> bool:
        """Check if a folder is currently being watched."""
