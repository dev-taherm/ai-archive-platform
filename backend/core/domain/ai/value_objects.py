from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class AIProvider(enum.Enum):
    """Supported AI/ML providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    AZURE = "azure"
    AWS_BEDROCK = "aws_bedrock"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for an AI model."""

    provider: AIProvider
    model_name: str
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    extra_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"Temperature must be 0.0-2.0, got {self.temperature}")
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be >= 1, got {self.max_tokens}")

    @property
    def is_local(self) -> bool:
        return self.provider == AIProvider.LOCAL

    @property
    def supports_streaming(self) -> bool:
        return self.provider in (
            AIProvider.OPENAI,
            AIProvider.ANTHROPIC,
            AIProvider.AZURE,
        )


class TaskStatus(enum.Enum):
    """Status of an AI task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    @property
    def is_terminal(self) -> bool:
        return self in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMEOUT,
        )

    @property
    def is_success(self) -> bool:
        return self == TaskStatus.COMPLETED
