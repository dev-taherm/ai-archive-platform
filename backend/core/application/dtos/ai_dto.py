from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AIResultDTO:
    """Data transfer object for AI processing results."""

    task_id: uuid.UUID
    task_type: str
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    processing_time_ms: float = 0.0
    tokens_used: int = 0
    model_used: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


@dataclass(frozen=True)
class EmbeddingDTO:
    """Data transfer object for embedding vectors."""

    id: str
    text: str
    vector: tuple[float, ...]
    source_type: str
    source_id: uuid.UUID
    chunk_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ClassificationDTO:
    """Data transfer object for classification operations."""

    input_text: str
    predicted_label: str
    confidence: float
    all_labels: dict[str, float] = field(default_factory=dict)
    model_used: str = ""
    classified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_high_confidence(self) -> bool:
        """Whether the classification confidence is high (>= 0.8)."""
        return self.confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        """Whether the classification confidence is low (< 0.5)."""
        return self.confidence < 0.5
