from __future__ import annotations

import logging
import uuid
from typing import Any

from core.application.dtos.search_dto import (
    SearchFiltersDTO,
    SearchQueryDTO,
    SearchResponseDTO,
    SearchResultDTO,
)
from core.application.interfaces.repositories import AuditLogRepository
from core.application.use_cases.search_use_cases import SearchUseCases

logger = logging.getLogger(__name__)


class SearchService:
    """Application service orchestrating search operations."""

    def __init__(
        self,
        search_use_cases: SearchUseCases,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._search_use_cases = search_use_cases
        self._audit_log_repository = audit_log_repository

    async def search(
        self,
        query_dto: SearchQueryDTO,
        *,
        user_id: uuid.UUID | None = None,
    ) -> SearchResponseDTO:
        """Execute a search and log the operation."""
        result = await self._search_use_cases.search(query_dto)

        await self._audit(
            action="search.executed",
            user_id=user_id,
            resource_type="search",
            resource_id=None,
            details={
                "query": query_dto.query,
                "search_type": query_dto.search_type,
                "result_count": result.total_count,
                "search_time_ms": result.search_time_ms,
            },
        )

        return result

    async def semantic_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
        user_id: uuid.UUID | None = None,
    ) -> list[SearchResultDTO]:
        """Execute a semantic search and log the operation."""
        results = await self._search_use_cases.semantic_search(
            query,
            max_results=max_results,
            offset=offset,
            filters=filters,
        )

        await self._audit(
            action="search.semantic",
            user_id=user_id,
            resource_type="search",
            resource_id=None,
            details={"query": query, "result_count": len(results)},
        )

        return results

    async def keyword_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
        user_id: uuid.UUID | None = None,
    ) -> list[SearchResultDTO]:
        """Execute a keyword search and log the operation."""
        results = await self._search_use_cases.keyword_search(
            query,
            max_results=max_results,
            offset=offset,
            filters=filters,
        )

        await self._audit(
            action="search.keyword",
            user_id=user_id,
            resource_type="search",
            resource_id=None,
            details={"query": query, "result_count": len(results)},
        )

        return results

    async def hybrid_search(
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
        """Execute a hybrid search and log the operation."""
        results = await self._search_use_cases.hybrid_search(
            query,
            max_results=max_results,
            offset=offset,
            filters=filters,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
        )

        await self._audit(
            action="search.hybrid",
            user_id=user_id,
            resource_type="search",
            resource_id=None,
            details={
                "query": query,
                "result_count": len(results),
                "semantic_weight": semantic_weight,
                "keyword_weight": keyword_weight,
            },
        )

        return results

    async def _audit(
        self,
        action: str,
        user_id: uuid.UUID | None,
        resource_type: str,
        resource_id: uuid.UUID | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Persist an audit log entry."""
        try:
            await self._audit_log_repository.save({
                "action": action,
                "user_id": str(user_id) if user_id else None,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "details": details or {},
            })
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)
