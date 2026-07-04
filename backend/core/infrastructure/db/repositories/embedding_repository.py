from __future__ import annotations

import uuid
from typing import Any, Sequence

import numpy as np
from django.db.models import QuerySet

from apps.ai.models import Embedding
from core.application.interfaces.repositories import EmbeddingRepository


class PgvectorEmbeddingRepository(EmbeddingRepository):
    """Django ORM implementation of EmbeddingRepository using numpy for similarity."""

    def __init__(self) -> None:
        self._model = Embedding

    def _qs(self) -> QuerySet:
        return self._model.objects.all()

    def save(
        self,
        vector_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        metadata = metadata or {}
        document_id = metadata.get("document_id")
        file_id = metadata.get("file_id")
        chunk_index = metadata.get("chunk_index", 0)

        obj, _created = self._qs().update_or_create(
            vector_id=vector_id,
            defaults={
                "embedding": embedding,
                "metadata": metadata,
                "document_id": uuid.UUID(document_id) if document_id else None,
                "file_id": uuid.UUID(file_id) if file_id else None,
                "chunk_index": chunk_index,
            },
        )
        return vector_id

    def search_similar(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> Sequence[tuple[str, float, dict[str, Any]]]:
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm

        qs = self._qs().exclude(embedding=[])
        if filter_metadata:
            if "document_id" in filter_metadata:
                qs = qs.filter(document_id=filter_metadata["document_id"])

        results: list[tuple[str, float, dict[str, Any]]] = []
        for obj in qs.iterator():
            if not obj.embedding:
                continue
            stored_vec = np.array(obj.embedding, dtype=np.float32)
            stored_norm = np.linalg.norm(stored_vec)
            if stored_norm > 0:
                stored_vec = stored_vec / stored_norm
            score = float(np.dot(query_vec, stored_vec))
            if score >= threshold:
                results.append((obj.vector_id, score, obj.metadata))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete(self, vector_id: str) -> bool:
        deleted, _count = self._qs().filter(vector_id=vector_id).delete()
        return deleted > 0

    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        qs = self._qs()
        if "document_id" in filter_metadata:
            qs = qs.filter(document_id=filter_metadata["document_id"])
        if "file_id" in filter_metadata:
            qs = qs.filter(file_id=filter_metadata["file_id"])
        _deleted, count = qs.delete()
        return count
