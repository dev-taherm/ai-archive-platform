from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.infrastructure.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """A single search result."""
    id: str
    text: str
    score: float
    document_id: str = ""
    chunk_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    match_type: str = "hybrid"  # "semantic", "keyword", "hybrid"


class HybridSearchService:
    """Combines semantic (vector) search with keyword (BM25-like) search.

    Merges results from both strategies with configurable weights.
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> None:
        self._vector_store = vector_store or VectorStore()
        self._semantic_weight = semantic_weight
        self._keyword_weight = keyword_weight

    def search(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        *,
        top_k: int = 10,
        threshold: float = 0.0,
        document_id: str | None = None,
        use_semantic: bool = True,
        use_keyword: bool = True,
    ) -> list[SearchResult]:
        """Run hybrid search combining semantic and keyword matching.

        Args:
            query: Natural language search query.
            query_embedding: Pre-computed embedding for the query (optional).
            top_k: Number of results to return.
            threshold: Minimum score threshold.
            document_id: Filter results to a specific document.
            use_semantic: Enable semantic (vector) search.
            use_keyword: Enable keyword search.

        Returns:
            Ranked list of SearchResult objects.
        """
        semantic_results: dict[str, dict] = {}
        keyword_results: dict[str, dict] = {}

        # Semantic search
        if use_semantic and query_embedding:
            raw_semantic = self._vector_store.search(
                query_embedding,
                top_k=top_k * 2,  # fetch more for fusion
                threshold=threshold,
                filter_metadata={"document_id": document_id} if document_id else None,
            )
            for r in raw_semantic:
                semantic_results[r["id"]] = r

        # Keyword search
        if use_keyword:
            raw_keyword = self._keyword_search(query, top_k=top_k * 2)
            if document_id:
                raw_keyword = [r for r in raw_keyword if r.get("metadata", {}).get("document_id") == document_id]
            for r in raw_keyword:
                keyword_results[r["id"]] = r

        # Score fusion (Reciprocal Rank Fusion)
        all_ids = set(semantic_results.keys()) | set(keyword_results.keys())
        scored: list[SearchResult] = []

        for entry_id in all_ids:
            sem_score = 0.0
            kw_score = 0.0
            text = ""
            meta: dict[str, Any] = {}

            if entry_id in semantic_results:
                sem_score = semantic_results[entry_id]["score"]
                text = semantic_results[entry_id]["text"]
                meta = semantic_results[entry_id].get("metadata", {})

            if entry_id in keyword_results:
                kw_score = keyword_results[entry_id]["score"]
                if not text:
                    text = keyword_results[entry_id]["text"]
                if not meta:
                    meta = keyword_results[entry_id].get("metadata", {})

            # Weighted combination
            combined = (
                self._semantic_weight * sem_score
                + self._keyword_weight * kw_score
            )

            # Determine match type
            if sem_score > 0 and kw_score > 0:
                match_type = "hybrid"
            elif sem_score > 0:
                match_type = "semantic"
            else:
                match_type = "keyword"

            if combined >= threshold:
                scored.append(SearchResult(
                    id=entry_id,
                    text=text,
                    score=combined,
                    document_id=meta.get("document_id", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    metadata=meta,
                    match_type=match_type,
                ))

        # Sort by score descending
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def _keyword_search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Simple keyword search using TF scoring."""
        if not query or not query.strip():
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        results: list[dict[str, Any]] = []

        for entry in self._vector_store._entries:
            entry_text = entry.get("text", "")
            entry_terms = self._tokenize(entry_text)

            if not entry_terms:
                continue

            # Compute term frequency score
            score = 0.0
            entry_term_set = set(entry_terms)
            for term in query_terms:
                if term in entry_term_set:
                    # Count occurrences
                    tf = entry_terms.count(term) / len(entry_terms)
                    # IDF-like weight (rarer terms score higher)
                    idf = 1.0  # simplified
                    score += tf * idf

            # Normalize by query length
            if query_terms:
                score /= len(query_terms)

            if score > 0:
                results.append({
                    "id": entry["id"],
                    "text": entry_text,
                    "score": min(score, 1.0),
                    "metadata": entry.get("metadata", {}),
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercasing tokenizer."""
        # Remove punctuation, lowercase, split
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        return [t for t in cleaned.split() if len(t) > 1]

    def index_document_chunks(
        self,
        document_id: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        """Index document chunks into the vector store.

        Args:
            document_id: UUID of the document.
            chunks: List of chunk dicts with 'text' and 'index' keys.
            embeddings: Corresponding embedding vectors.

        Returns:
            Number of chunks indexed.
        """
        if not chunks or not embeddings:
            return 0

        ids = []
        texts = []
        metas = []

        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = f"{document_id}_chunk_{chunk.get('index', 0)}"
            ids.append(chunk_id)
            texts.append(chunk["text"])
            metas.append({
                "document_id": document_id,
                "chunk_index": chunk.get("index", 0),
                "start": chunk.get("start", 0),
                "end": chunk.get("end", 0),
            })

        count = self._vector_store.add_batch(ids, texts, embeddings, metas)
        self._vector_store._save()
        logger.info("Indexed %d chunks for document %s", count, document_id)
        return count
