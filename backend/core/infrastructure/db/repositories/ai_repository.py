from __future__ import annotations

import uuid
from typing import Any, Sequence

from django.db.models import QuerySet

from core.application.interfaces.repositories import AITaskRepository


class DjangoAITaskRepository(AITaskRepository):
    """Django ORM implementation of AITaskRepository ABC.

    Uses apps.ai.models.AITask as the canonical ORM model.
    """

    def __init__(self) -> None:
        from apps.ai.models import AITask as AITaskModel
        self._model = AITaskModel

    def _qs(self) -> QuerySet:
        return self._model.objects.all()

    async def get_by_id(self, task_id: uuid.UUID) -> dict[str, Any] | None:
        try:
            obj = await self._qs().aget(id=task_id)
            return {
                "id": str(obj.id),
                "task_type": obj.task_type,
                "status": obj.status,
                "document_id": str(obj.document_id) if obj.document_id else None,
                "user_id": str(obj.user_id) if obj.user_id else None,
                "input_preview": obj.input_preview,
                "result": obj.result,
                "error_message": obj.error_message,
                "processing_time_ms": obj.processing_time_ms,
                "tokens_used": obj.tokens_used,
                "model_used": obj.model_used,
                "created_at": obj.created_at.isoformat(),
                "completed_at": obj.completed_at.isoformat() if obj.completed_at else None,
            }
        except self._model.DoesNotExist:
            return None

    async def save(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("id")
        if task_id:
            try:
                obj = await self._qs().aget(id=task_id)
                for field in (
                    "task_type", "status", "document_id", "user_id",
                    "input_preview", "result", "error_message",
                    "processing_time_ms", "tokens_used", "model_used",
                    "completed_at",
                ):
                    if field in task:
                        setattr(obj, field, task[field])
                obj.save()
                return task
            except self._model.DoesNotExist:
                pass

        obj = self._model.objects.create(
            task_type=task.get("task_type", ""),
            status=task.get("status", "pending"),
            document_id=task.get("document_id"),
            user_id=task.get("user_id"),
            input_preview=task.get("input_preview", ""),
            result=task.get("result", {}),
            error_message=task.get("error_message", ""),
            tokens_used=task.get("tokens_used", 0),
            model_used=task.get("model_used", ""),
        )
        task["id"] = str(obj.id)
        return task

    async def list_pending(
        self,
        *,
        task_type: str | None = None,
        limit: int = 50,
    ) -> Sequence[dict[str, Any]]:
        qs = self._qs().filter(status="pending").order_by("created_at")
        if task_type:
            qs = qs.filter(task_type=task_type)
        qs = qs[:limit]
        results: list[dict[str, Any]] = []
        async for obj in qs:
            results.append({
                "id": str(obj.id),
                "task_type": obj.task_type,
                "status": obj.status,
                "document_id": str(obj.document_id) if obj.document_id else None,
                "input_preview": obj.input_preview,
            })
        return results


class DjangoEmbeddingRepository:
    """Placeholder for embedding repository - uses pgvector via EmbeddingService."""

    async def save(
        self,
        vector_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return vector_id

    async def search_similar(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> Sequence[tuple[str, float, dict[str, Any]]]:
        return []

    async def delete(self, vector_id: str) -> bool:
        return False

    async def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        return 0
