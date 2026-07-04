from __future__ import annotations

from typing import Any, Sequence


from apps.ai.models import Embedding as DjangoEmbedding
from core.application.interfaces.repositories import EmbeddingRepository


class DjangoEmbeddingRepository(EmbeddingRepository):
    """Django ORM implementation of the EmbeddingRepository interface."""

    def save(
        self,
        vector_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        orm, _ = DjangoEmbedding.objects.update_or_create(
            vector_id=vector_id,
            defaults={
                "embedding": embedding,
                "metadata": metadata or {},
            },
        )
        return orm.vector_id

    def search_similar(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> Sequence[tuple[str, float, dict[str, Any]]]:
        qs = DjangoEmbedding.objects.all()

        if filter_metadata:
            for key, value in filter_metadata.items():
                qs = qs.filter(**{f"metadata__{key}": value})

        results: list[tuple[str, float, dict[str, Any]]] = []
        for orm in qs:
            stored = orm.embedding
            if not stored:
                continue
            similarity = self._cosine_similarity(query_embedding, stored)
            if similarity >= threshold:
                results.append((orm.vector_id, similarity, orm.metadata))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete(self, vector_id: str) -> bool:
        deleted, _ = DjangoEmbedding.objects.filter(vector_id=vector_id).delete()
        return deleted > 0

    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        qs = DjangoEmbedding.objects.all()
        for key, value in filter_metadata.items():
            qs = qs.filter(**{f"metadata__{key}": value})
        deleted_count = qs.count()
        qs.delete()
        return deleted_count

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            min_len = min(len(a), len(b))
            a, b = a[:min_len], b[:min_len]

        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5

        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
