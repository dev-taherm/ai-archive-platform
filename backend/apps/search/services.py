from __future__ import annotations

import logging
import uuid

from core.application.dtos.search_dto import (
    SearchFiltersDTO,
    SearchQueryDTO,
    SearchResponseDTO,
    SearchResultDTO,
)
from core.application.use_cases.search_use_cases import SearchUseCases

logger = logging.getLogger(__name__)


class SearchService:
    """Thin wrapper delegating search operations to core SearchUseCases."""

    def __init__(self, search_use_cases: SearchUseCases) -> None:
        self._search_use_cases = search_use_cases

    def search(
        self,
        query_dto: SearchQueryDTO,
        *,
        user_id: uuid.UUID | None = None,
    ) -> SearchResponseDTO:
        """Execute a search using the specified strategy."""
        import asyncio
        result = asyncio.run(self._search_use_cases.search(query_dto))
        logger.info(
            "Search: query=%s type=%s results=%d time=%.1fms",
            query_dto.query[:50],
            query_dto.search_type,
            result.total_count,
            result.search_time_ms,
        )
        return result

    def semantic_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
        user_id: uuid.UUID | None = None,
    ) -> list[SearchResultDTO]:
        """Search by semantic similarity using embeddings."""
        import asyncio
        return asyncio.run(self._search_use_cases.semantic_search(
            query,
            max_results=max_results,
            offset=offset,
            filters=filters,
        ))

    def keyword_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
        user_id: uuid.UUID | None = None,
    ) -> list[SearchResultDTO]:
        """Search by keyword matching within document chunks."""
        import asyncio
        return asyncio.run(self._search_use_cases.keyword_search(
            query,
            max_results=max_results,
            offset=offset,
            filters=filters,
        ))

    def hybrid_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        user_id: uuid.UUID | None = None,
    ) -> list[SearchResultDTO]:
        """Combine semantic and keyword search with weighted scoring."""
        import asyncio
        return asyncio.run(self._search_use_cases.hybrid_search(
            query,
            max_results=max_results,
            offset=offset,
            filters=filters,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
        ))
