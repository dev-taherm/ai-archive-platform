from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.domain.ai.value_objects import AIProvider, ModelConfig, TaskStatus
from core.domain.common.entities import BaseEntity


@dataclass(frozen=True)
class Embedding:
    """Represents a vector embedding for a piece of content."""

    id: str
    vector: tuple[float, ...]
    content_id: uuid.UUID
    model: str = ""
    dimensions: int = 0

    def __post_init__(self) -> None:
        if not self.vector:
            raise ValueError("Embedding vector cannot be empty")
        if self.dimensions == 0:
            object.__setattr__(self, "dimensions", len(self.vector))

    @property
    def magnitude(self) -> float:
        return sum(v * v for v in self.vector) ** 0.5

    def normalized(self) -> Embedding:
        """Return a unit-length copy of this embedding."""
        mag = self.magnitude
        if mag == 0:
            return self
        return Embedding(
            id=self.id,
            vector=tuple(v / mag for v in self.vector),
            content_id=self.content_id,
            model=self.model,
            dimensions=self.dimensions,
        )


@dataclass(frozen=True)
class AIResult(BaseEntity):
    """Result produced by an AI task."""

    task_id: uuid.UUID = field(default_factory=uuid.uuid4)
    output: dict[str, Any] = field(default_factory=dict)
    token_usage: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    model_version: str = ""
    confidence: float = 0.0

    @property
    def tokens_per_second(self) -> float:
        if self.latency_ms <= 0:
            return 0.0
        return round(self.token_usage / (self.latency_ms / 1000), 2)


@dataclass(frozen=True)
class AITask(BaseEntity):
    """Represents a unit of AI work to be performed."""

    task_type: str = ""
    provider: AIProvider = AIProvider.LOCAL
    model_config: ModelConfig = field(default_factory=lambda: ModelConfig(provider=AIProvider.LOCAL, model_name="default"))
    input_data: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result_id: uuid.UUID | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    priority: int = 0
    tags: tuple[str, ...] = ()

    def start(self) -> None:
        object.__setattr__(self, "status", TaskStatus.RUNNING)
        object.__setattr__(self, "started_at", datetime.now(timezone.utc))
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def complete(self, result_id: uuid.UUID) -> None:
        object.__setattr__(self, "status", TaskStatus.COMPLETED)
        object.__setattr__(self, "result_id", result_id)
        object.__setattr__(self, "completed_at", datetime.now(timezone.utc))
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def fail(self, error: str) -> None:
        object.__setattr__(self, "status", TaskStatus.FAILED)
        object.__setattr__(self, "error_message", error)
        object.__setattr__(self, "completed_at", datetime.now(timezone.utc))
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def cancel(self) -> None:
        object.__setattr__(self, "status", TaskStatus.CANCELLED)
        object.__setattr__(self, "completed_at", datetime.now(timezone.utc))
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    @property
    def is_running(self) -> bool:
        return self.status == TaskStatus.RUNNING

    @property
    def duration_ms(self) -> float | None:
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000
