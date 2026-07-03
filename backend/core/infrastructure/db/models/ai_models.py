from __future__ import annotations

from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.db import models
from pgvector.django import VectorField

from core.domain.ai.entities import AIResult, AITask, Embedding
from core.domain.ai.value_objects import AIProvider, ModelConfig, TaskStatus
from core.infrastructure.db.models.base import BaseModel


class AITaskModel(BaseModel):
    """Django ORM model for AITask domain entity."""

    task_type = models.CharField(max_length=100, db_index=True)
    provider = models.CharField(
        max_length=30,
        choices=[(p.value, p.value) for p in AIProvider],
    )
    model_name = models.CharField(max_length=200)
    temperature = models.FloatField(default=0.0)
    max_tokens = models.IntegerField(default=4096)
    top_p = models.FloatField(default=1.0)
    extra_params = models.JSONField(default=dict, blank=True)
    input_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in TaskStatus],
        default=TaskStatus.PENDING.value,
        db_index=True,
    )
    result_id = models.UUIDField(null=True, blank=True, db_index=True)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(default=0)
    tags = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
    )

    class Meta:
        db_table = "ai_task"
        indexes = [
            models.Index(fields=["status", "task_type"], name="idx_aitask_status_type"),
            models.Index(fields=["priority"], name="idx_aitask_priority"),
            models.Index(fields=["provider"], name="idx_aitask_provider"),
        ]

    def __str__(self) -> str:
        return f"AITask({self.task_type}, status={self.status})"

    def to_domain(self) -> AITask:
        return AITask(
            id=self.id,
            task_type=self.task_type,
            provider=AIProvider(self.provider),
            model_config=ModelConfig(
                provider=AIProvider(self.provider),
                model_name=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                extra_params=dict(self.extra_params) if self.extra_params else {},
            ),
            input_data=dict(self.input_data) if self.input_data else {},
            status=TaskStatus(self.status),
            result_id=self.result_id,
            error_message=self.error_message,
            started_at=self.started_at,
            completed_at=self.completed_at,
            priority=self.priority,
            tags=list(self.tags) if self.tags else [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: AITask) -> AITaskModel:
        return cls(
            id=entity.id,
            task_type=entity.task_type,
            provider=entity.provider.value,
            model_name=entity.model_config.model_name,
            temperature=entity.model_config.temperature,
            max_tokens=entity.model_config.max_tokens,
            top_p=entity.model_config.top_p,
            extra_params=entity.model_config.extra_params,
            input_data=entity.input_data,
            status=entity.status.value,
            result_id=entity.result_id,
            error_message=entity.error_message,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            priority=entity.priority,
            tags=entity.tags,
        )


class AIResultModel(BaseModel):
    """Django ORM model for AIResult domain entity."""

    task = models.OneToOneField(
        AITaskModel,
        on_delete=models.CASCADE,
        related_name="result",
    )
    output = models.JSONField(default=dict, blank=True)
    token_usage = models.PositiveIntegerField(default=0)
    latency_ms = models.FloatField(default=0.0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    model_version = models.CharField(max_length=100, blank=True, default="")
    confidence = models.FloatField(default=0.0)

    class Meta:
        db_table = "ai_result"

    def __str__(self) -> str:
        return f"AIResult(task={self.task_id})"

    def to_domain(self) -> AIResult:
        return AIResult(
            id=self.id,
            task_id=self.task_id,
            output=dict(self.output) if self.output else {},
            token_usage=self.token_usage,
            latency_ms=self.latency_ms,
            cost_usd=float(self.cost_usd),
            model_version=self.model_version,
            confidence=self.confidence,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: AIResult) -> AIResultModel:
        return cls(
            id=entity.id,
            task_id=entity.task_id,
            output=entity.output,
            token_usage=entity.token_usage,
            latency_ms=entity.latency_ms,
            cost_usd=entity.cost_usd,
            model_version=entity.model_version,
            confidence=entity.confidence,
        )


class EmbeddingModel(BaseModel):
    """Django ORM model for Embedding domain entity with pgvector support.

    Uses the pgvector VectorField for efficient similarity search via
    approximate nearest neighbor (HNSW / IVFFlat) indexes.
    """

    vector_id = models.CharField(max_length=255, unique=True, db_index=True)
    content_id = models.UUIDField(db_index=True)
    model = models.CharField(max_length=200, blank=True, default="")
    dimensions = models.PositiveIntegerField(default=0)
    vector = VectorField(dimensions=1536)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "embedding"
        indexes = [
            models.Index(fields=["content_id"], name="idx_embedding_content"),
            models.Index(fields=["model"], name="idx_embedding_model"),
        ]

    def __str__(self) -> str:
        return f"Embedding({self.vector_id}, dims={self.dimensions})"

    def to_domain(self) -> Embedding:
        vec = list(self.vector) if self.vector else []
        return Embedding(
            id=self.vector_id,
            vector=tuple(vec),
            content_id=self.content_id,
            model=self.model,
            dimensions=self.dimensions,
        )

    @classmethod
    def from_domain(cls, entity: Embedding) -> EmbeddingModel:
        return cls(
            vector_id=entity.id,
            content_id=entity.content_id,
            model=entity.model,
            dimensions=entity.dimensions,
            vector=list(entity.vector),
        )
