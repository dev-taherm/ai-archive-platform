from __future__ import annotations

import uuid
from typing import Any, Sequence


from apps.ai.models import AITask as DjangoAITask
from core.application.interfaces.repositories import AITaskRepository


class DjangoAITaskRepository(AITaskRepository):
    """Django ORM implementation of the AITaskRepository interface."""

    def get_by_id(self, task_id: uuid.UUID) -> dict[str, Any] | None:
        try:
            orm = DjangoAITask.objects.get(pk=task_id)
            return self._to_dict(orm)
        except DjangoAITask.DoesNotExist:
            return None

    def save(self, task: dict[str, Any]) -> dict[str, Any]:
        orm = self._to_orm(task)
        orm.save()
        return self._to_dict(orm)

    def list_pending(
        self,
        *,
        task_type: str | None = None,
        limit: int = 50,
    ) -> Sequence[dict[str, Any]]:
        qs = DjangoAITask.objects.filter(status=DjangoAITask.Status.PENDING)
        if task_type:
            qs = qs.filter(task_type=task_type)
        qs = qs.order_by("created_at")[:limit]
        return [self._to_dict(orm) for orm in qs]

    @staticmethod
    def _to_dict(orm: DjangoAITask) -> dict[str, Any]:
        return {
            "id": orm.id,
            "task_type": orm.task_type,
            "status": orm.status,
            "document_id": orm.document_id,
            "user_id": orm.user_id,
            "input_preview": orm.input_preview,
            "result": orm.result,
            "error_message": orm.error_message,
            "processing_time_ms": orm.processing_time_ms,
            "tokens_used": orm.tokens_used,
            "model_used": orm.model_used,
            "created_at": orm.created_at,
            "completed_at": orm.completed_at,
        }

    @staticmethod
    def _to_orm(data: dict[str, Any]) -> DjangoAITask:
        task_id = data.get("id")
        orm = DjangoAITask(
            task_type=data.get("task_type", ""),
            status=data.get("status", DjangoAITask.Status.PENDING),
            document_id=data.get("document_id"),
            user_id=data.get("user_id"),
            input_preview=data.get("input_preview", ""),
            result=data.get("result", {}),
            error_message=data.get("error_message", ""),
            processing_time_ms=data.get("processing_time_ms"),
            tokens_used=data.get("tokens_used", 0),
            model_used=data.get("model_used", ""),
            completed_at=data.get("completed_at"),
        )
        if task_id:
            orm.pk = task_id
        return orm
