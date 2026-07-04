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

    def _get_embeddings(self) -> Any:
        """Lazy-initialise the LangChain embeddings instance."""
        if self._embeddings is not None:
            return self._embeddings

        if self._provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings

                api_key = self._api_key or os.environ.get("OPENAI_API_KEY", "")
                self._embeddings = OpenAIEmbeddings(
                    model=self._model_name,
                    api_key=api_key,
                    dimensions=self._dimensions,
                )
            except ImportError:
                raise ImportError(
                    "langchain-openai is required: pip install langchain-openai"
                )

        elif self._provider == "ollama":
            try:
                from langchain_ollama import OllamaEmbeddings

                base_url = self._base_url or os.environ.get(
                    "OLLAMA_BASE_URL", "http://localhost:11434"
                )
                self._embeddings = OllamaEmbeddings(
                    model=self._model_name,
                    base_url=base_url,
                )
            except ImportError:
                raise ImportError(
                    "langchain-ollama is required: pip install langchain-ollama"
                )

        elif self._provider == "huggingface":
            try:
                from langchain_huggingface import HuggingFaceEmbeddings

                self._embeddings = HuggingFaceEmbeddings(
                    model_name=self._model_name,
                )
            except ImportError:
                raise ImportError(
                    "langchain-huggingface is required: pip install langchain-huggingface"
                )

        else:
            raise ValueError(
                f"Unsupported embedding provider: {self._provider!r}. "
                "Supported: openai, ollama, huggingface"
            )

        logger.info(
            "LangChain embeddings initialised (provider=%s, model=%s)",
            self._provider,
            self._model_name,
        )
        return self._embeddings

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""
        embeddings = self._get_embeddings()
        return embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts with batching."""
        if not texts:
            return []

        embeddings = self._get_embeddings()

        # Process in batches to avoid API rate limits and memory issues
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
