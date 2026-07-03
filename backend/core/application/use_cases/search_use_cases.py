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
from core.application.interfaces.repositories import (
    DocumentRepository,
    EmbeddingRepository,
    FileRepository,
)
from core.application.interfaces.services import EmbeddingProvider

logger = logging.getLogger(__name__)


class SearchUseCases:
    """Use cases for search operations across the archive."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_repository: EmbeddingRepository,
        file_repository: FileRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._document_repository = document_repository
        self._embedding_repository = embedding_repository
        self._file_repository = file_repository
        self._embedding_provider = embedding_provider

    async def search(self, query_dto: SearchQueryDTO) -> SearchResponseDTO:
        """Execute a search using the specified strategy."""
        if not query_dto.query.strip():
            return SearchResponseDTO(
                query=query_dto.query,
                results=(),
                total_count=0,
                search_time_ms=0.0,
                search_type=query_dto.search_type,
            )

        import time

        start = time.monotonic()

        if query_dto.search_type == "semantic":
            results = await self.semantic_search(
                query_dto.query,
                max_results=query_dto.max_results,
                offset=query_dto.offset,
                filters=query_dto.filters,
            )
        elif query_dto.search_type == "keyword":
            results = await self.keyword_search(
                query_dto.query,
                max_results=query_dto.max_results,
                offset=query_dto.offset,
                filters=query_dto.filters,
            )
        else:
            results = await self.hybrid_search(
                query_dto.query,
                max_results=query_dto.max_results,
                offset=query_dto.offset,
                filters=query_dto.filters,
            )

        elapsed_ms = (time.monotonic() - start) * 1000

        return SearchResponseDTO(
            query=query_dto.query,
            results=tuple(results),
            total_count=len(results),
            search_time_ms=round(elapsed_ms, 2),
            search_type=query_dto.search_type,
            applied_filters=query_dto.filters,
        )

    async def semantic_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
    ) -> list[SearchResultDTO]:
        """Search by semantic similarity using embeddings."""
        query_embedding = await self._embedding_provider.embed_text(query)

        filter_meta: dict[str, Any] | None = None
        if filters:
            filter_meta = self._build_filter_metadata(filters)

        similar_chunks = await self._embedding_repository.search_similar(
            query_embedding,
            top_k=max_results + offset,
            threshold=filters.min_score if filters else 0.0,
            filter_metadata=filter_meta,
        )

        results: list[SearchResultDTO] = []
        rank = 0
        for chunk_id, score, metadata in similar_chunks[offset : offset + max_results]:
            rank += 1
            doc_id = metadata.get("document_id")
            file_id = metadata.get("file_id")

            if doc_id is None or file_id is None:
                continue

            results.append(
                SearchResultDTO(
                    document_id=uuid.UUID(doc_id),
                    file_id=uuid.UUID(file_id),
                    title=metadata.get("title", ""),
                    snippet=metadata.get("content", "")[:300],
                    score=score,
                    rank=rank,
                    doc_type=metadata.get("doc_type", "unknown"),
                    language=metadata.get("language", "unknown"),
                    match_source="semantic",
                )
            )

        return results

    async def keyword_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
    ) -> list[SearchResultDTO]:
        """Search by keyword matching within document chunks."""
        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        documents = await self._document_repository.list_all(offset=0, limit=10000)
        results: list[SearchResultDTO] = []

        for doc in documents:
            if not doc.extracted_text:
                continue

            text_lower = doc.extracted_text.lower()
            if not query_lower in text_lower and not query_tokens.intersection(set(text_lower.split())):
                continue

            score = sum(1 for token in query_tokens if token in text_lower) / max(len(query_tokens), 1)

            if filters and filters.min_score > 0 and score < filters.min_score:
                continue

            snippet = self._extract_snippet(doc.extracted_text, query_lower)

            results.append(
                SearchResultDTO(
                    document_id=doc.id,
                    file_id=doc.file_id,
                    title=doc.metadata.title,
                    snippet=snippet,
                    score=score,
                    rank=0,
                    doc_type=doc.doc_type.value,
                    language=doc.metadata.language.value,
                    match_source="keyword",
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)

        for i, result in enumerate(results):
            results[i] = SearchResultDTO(
                document_id=result.document_id,
                file_id=result.file_id,
                title=result.title,
                snippet=result.snippet,
                score=result.score,
                rank=i + 1,
                doc_type=result.doc_type,
                language=result.language,
                match_source=result.match_source,
                highlights=result.highlights,
                metadata=result.metadata,
            )

        return results[offset : offset + max_results]

    async def hybrid_search(
        self,
        query: str,
        *,
        max_results: int = 20,
        offset: int = 0,
        filters: SearchFiltersDTO | None = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> list[SearchResultDTO]:
        """Combine semantic and keyword search with weighted scoring."""
        semantic_results = await self.semantic_search(
            query,
            max_results=max_results * 2,
            offset=0,
            filters=filters,
        )
        keyword_results = await self.keyword_search(
            query,
            max_results=max_results * 2,
            offset=0,
            filters=filters,
        )

        merged: dict[uuid.UUID, SearchResultDTO] = {}
        scores: dict[uuid.UUID, float] = {}

        for result in semantic_results:
            merged[result.document_id] = result
            scores[result.document_id] = result.score * semantic_weight

        for result in keyword_results:
            doc_id = result.document_id
            if doc_id in merged:
                scores[doc_id] += result.score * keyword_weight
            else:
                merged[doc_id] = result
                scores[doc_id] = result.score * keyword_weight

        ranked = sorted(merged.values(), key=lambda r: scores[r.document_id], reverse=True)

        final_results: list[SearchResultDTO] = []
        for i, result in enumerate(ranked[offset : offset + max_results]):
            final_results.append(
                SearchResultDTO(
                    document_id=result.document_id,
                    file_id=result.file_id,
                    title=result.title,
                    snippet=result.snippet,
                    score=scores[result.document_id],
                    rank=i + 1,
                    doc_type=result.doc_type,
                    language=result.language,
                    match_source="hybrid",
                    highlights=result.highlights,
                    metadata=result.metadata,
                )
            )

        return final_results

    @staticmethod
    def _extract_snippet(text: str, query: str, context_chars: int = 150) -> str:
        """Extract a relevant snippet around the query occurrence."""
        lower_text = text.lower()
        idx = lower_text.find(query)
        if idx == -1:
            return text[:context_chars * 2]

        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(query) + context_chars)
        snippet = text[start:end]

        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{snippet}{suffix}"

    @staticmethod
    def _build_filter_metadata(filters: SearchFiltersDTO) -> dict[str, Any]:
        """Convert search filters to metadata dict for embedding repository."""
        meta: dict[str, Any] = {}
        if filters.doc_types:
            meta["doc_type"] = {"$in": list(filters.doc_types)}
        if filters.languages:
            meta["language"] = {"$in": list(filters.languages)}
        if filters.tags:
            meta["tags"] = {"$in": list(filters.tags)}
        return meta
