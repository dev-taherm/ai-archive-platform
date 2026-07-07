from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.domain.documents.value_objects import Confidence, Language


class OCRProvider(ABC):
    """Abstract interface for OCR text extraction."""

    @abstractmethod
    def extract_text(
        self,
        content: bytes,
        *,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        """Extract text content from a document or image via OCR."""

    @abstractmethod
    def detect_language(self, text: str) -> Language:
        """Detect the primary language of the given text."""

    @abstractmethod
    def get_confidence(self, text: str) -> Confidence:
        """Return the confidence score of the OCR extraction."""

    def extract_with_boxes(
        self,
        content: bytes,
        *,
        content_type: str,
    ) -> list[dict[str, Any]]:
        """Extract text with bounding boxes and confidence scores.

        Returns list of dicts with keys: bbox, text, confidence.
        Default implementation returns empty list.
        """
        return []


class LLMProvider(ABC):
    """Abstract interface for large language model operations."""

    @abstractmethod
    def classify(
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
    def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Extract structured data fields from text."""

    @abstractmethod
    def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a concise summary of the given text."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Have a conversational exchange with the LLM."""

    def extract_entities(
        self,
        text: str,
        *,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract named entities from text.

        Returns list of dicts with keys: name, type, context.
        Default implementation returns empty list.
        """
        return []


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Implementations may batch requests for efficiency.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""

    @property
    def model_name(self) -> str:
        """Return the name of the embedding model."""
        return "unknown"


