from __future__ import annotations

import logging
import os
from typing import Any

from core.application.interfaces.services import EmbeddingProvider

logger = logging.getLogger(__name__)


class LangChainEmbeddingProvider(EmbeddingProvider):
    """LangChain-based implementation of EmbeddingProvider ABC.

    Uses LangChain's embedding abstractions to support OpenAI, Ollama,
    HuggingFace, and other embedding backends through a unified interface.
    Falls back to local HuggingFace embeddings when the primary provider fails.
    """

    def __init__(
        self,
        *,
        model_name: str = "text-embedding-3-small",
        provider: str = "openai",
        api_key: str | None = None,
        base_url: str | None = None,
        dimensions: int = 1536,
        batch_size: int = 64,
    ) -> None:
        self._model_name = model_name
        self._provider = provider.lower()
        self._api_key = api_key
        self._base_url = base_url
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._embeddings: Any = None
        self._fallback_embeddings: Any = None

    def _get_embeddings(self) -> Any:
        """Lazy-initialise the LangChain embeddings instance.

        Does NOT fallback on init failure — lets the caller handle it.
        """
        if self._embeddings is not None:
            return self._embeddings

        self._embeddings = self._create_embeddings(self._provider)

        logger.info(
            "LangChain embeddings initialised (provider=%s, model=%s)",
            self._provider,
            self._model_name,
        )
        return self._embeddings

    def _get_fallback_embeddings(self) -> Any:
        """Lazy-initialise a local FastEmbed fallback for query-time failures."""
        if self._fallback_embeddings is not None:
            return self._fallback_embeddings
        try:
            self._fallback_embeddings = self._create_embeddings("fastembed")
            logger.info("FastEmbed fallback loaded (BAAI/bge-small-en-v1.5)")
        except Exception as e:
            logger.error("FastEmbed fallback also failed: %s", e)
            raise
        return self._fallback_embeddings

    def _create_embeddings(self, provider: str) -> Any:
        """Create an embeddings instance for the given provider."""
        if provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings

                api_key = self._api_key or os.environ.get("OPENAI_API_KEY", "")
                return OpenAIEmbeddings(
                    model=self._model_name,
                    api_key=api_key,
                    dimensions=self._dimensions,
                )
            except ImportError:
                raise ImportError(
                    "langchain-openai is required: pip install langchain-openai"
                )

        elif provider == "google":
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                api_key = self._api_key or os.environ.get("GOOGLE_API_KEY", "")
                return GoogleGenerativeAIEmbeddings(
                    model="text-embedding-004",
                    google_api_key=api_key,
                )
            except ImportError:
                raise ImportError(
                    "langchain-google-genai is required: pip install langchain-google-genai"
                )

        elif provider == "ollama":
            try:
                from langchain_ollama import OllamaEmbeddings

                base_url = self._base_url or os.environ.get(
                    "OLLAMA_BASE_URL", "http://localhost:11434"
                )
                return OllamaEmbeddings(
                    model=self._model_name,
                    base_url=base_url,
                )
            except ImportError:
                raise ImportError(
                    "langchain-ollama is required: pip install langchain-ollama"
                )

        elif provider == "huggingface":
            try:
                from langchain_huggingface import HuggingFaceEndpointEmbeddings

                return HuggingFaceEndpointEmbeddings(
                    model="sentence-transformers/all-MiniLM-L6-v2",
                )
            except ImportError:
                raise ImportError(
                    "langchain-huggingface is required: pip install langchain-huggingface"
                )

        elif provider == "fastembed":
            return FastEmbedProvider()

        else:
            raise ValueError(
                f"Unsupported embedding provider: {provider!r}. "
                "Supported: openai, google, ollama, huggingface"
            )

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Raises on failure — caller decides fallback strategy.
        """
        embeddings = self._get_embeddings()
        return embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts with batching.

        Raises on failure — caller decides fallback strategy.
        """
        if not texts:
            return []

        embeddings = self._get_embeddings()
        all_results: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            batch_results = embeddings.embed_documents(batch)
            all_results.extend(batch_results)
        return all_results

    @property
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        return self._dimensions

    @property
    def model_name(self) -> str:
        """Return the name of the embedding model."""
        return self._model_name


class FastEmbedProvider:
    """Local embedding provider using fastembed (no API key needed).

    Uses BAAI/bge-small-en-v1.5 — 384-dim model that runs fully offline.
    Compatible with LangChain's embed_query/embed_documents interface.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name)
        self._dim: int | None = None

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        embeddings = list(self._model.embed([text]))
        if self._dim is None:
            self._dim = len(embeddings[0])
        return embeddings[0].tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple document texts."""
        if not texts:
            return []
        embeddings = list(self._model.embed(texts))
        if self._dim is None:
            self._dim = len(embeddings[0])
        return [e.tolist() for e in embeddings]
