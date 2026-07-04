from __future__ import annotations

import logging
from typing import Any

from core.infrastructure.agents.base_agent import BaseAgent
from core.infrastructure.services.embedding_service import LangChainEmbeddingProvider
from core.infrastructure.services.hybrid_search import HybridSearchService, SearchResult

logger = logging.getLogger(__name__)


class SearchAgent(BaseAgent):
    """Agent responsible for semantic, keyword, and hybrid search.

    Supported actions:
        - search:          Run hybrid search (semantic + keyword).
        - semantic_search: Pure vector-based semantic search.
        - keyword_search:  Pure keyword-based search.
    """

    def __init__(
        self,
        search_service: HybridSearchService | None = None,
        embedding_provider: LangChainEmbeddingProvider | None = None,
    ) -> None:
        super().__init__(name="SearchAgent")
        self._embedding = embedding_provider or LangChainEmbeddingProvider()
        self._search = search_service or HybridSearchService()

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if not action:
            return self._error("Missing required field: action")

        try:
            if action == "search":
                return await self._hybrid_search(task)
            if action == "semantic_search":
                return await self._semantic_search(task)
            if action == "keyword_search":
                return await self._keyword_search(task)
            return self._error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("SearchAgent action=%s failed", action)
            return self._error(str(exc))

    # ── helpers ───────────────────────────────────────────────────
    def _get_embedding(self, query: str) -> list[float]:
        return self._embedding.embed_text(query)

    def _format_results(self, results: list[SearchResult]) -> list[dict[str, Any]]:
        return [
            {
                "id": r.id,
                "text": r.text,
                "score": round(r.score, 4),
                "document_id": r.document_id,
                "chunk_index": r.chunk_index,
                "match_type": r.match_type,
                "metadata": r.metadata,
            }
            for r in results
        ]

    # ── actions ───────────────────────────────────────────────────
    async def _hybrid_search(self, task: dict[str, Any]) -> dict[str, Any]:
        query = task.get("query")
        if not query:
            return self._error("query is required for search")

        top_k = task.get("top_k", 10)
        threshold = task.get("threshold", 0.0)
        document_id = task.get("document_id")

        query_embedding = self._get_embedding(query)

        results = self._search.search(
            query,
            query_embedding=query_embedding,
            top_k=top_k,
            threshold=threshold,
            document_id=document_id,
            use_semantic=True,
            use_keyword=True,
        )

        logger.info("Hybrid search for %r: %d results", query[:50], len(results))
        return self._ok(
            data={
                "query": query,
                "results": self._format_results(results),
                "count": len(results),
                "search_type": "hybrid",
            },
            message=f"Found {len(results)} results",
        )

    async def _semantic_search(self, task: dict[str, Any]) -> dict[str, Any]:
        query = task.get("query")
        if not query:
            return self._error("query is required for semantic_search")

        top_k = task.get("top_k", 10)
        threshold = task.get("threshold", 0.0)
        document_id = task.get("document_id")

        query_embedding = self._get_embedding(query)

        results = self._search.search(
            query,
            query_embedding=query_embedding,
            top_k=top_k,
            threshold=threshold,
            document_id=document_id,
            use_semantic=True,
            use_keyword=False,
        )

        logger.info("Semantic search for %r: %d results", query[:50], len(results))
        return self._ok(
            data={
                "query": query,
                "results": self._format_results(results),
                "count": len(results),
                "search_type": "semantic",
            },
            message=f"Found {len(results)} results",
        )

    async def _keyword_search(self, task: dict[str, Any]) -> dict[str, Any]:
        query = task.get("query")
        if not query:
            return self._error("query is required for keyword_search")

        top_k = task.get("top_k", 10)
        threshold = task.get("threshold", 0.0)
        document_id = task.get("document_id")

        results = self._search.search(
            query,
            query_embedding=None,
            top_k=top_k,
            threshold=threshold,
            document_id=document_id,
            use_semantic=False,
            use_keyword=True,
        )

        logger.info("Keyword search for %r: %d results", query[:50], len(results))
        return self._ok(
            data={
                "query": query,
                "results": self._format_results(results),
                "count": len(results),
                "search_type": "keyword",
            },
            message=f"Found {len(results)} results",
        )
