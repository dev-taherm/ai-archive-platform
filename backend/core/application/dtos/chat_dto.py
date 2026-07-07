from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ChatMessageDTO:
    """Data transfer object for a chat message."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    session_id: uuid.UUID = field(default_factory=uuid.uuid4)
    role: str = "user"
    content: str = ""
    sources: tuple[dict[str, Any], ...] = ()
    tool_calls: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    model_used: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ChatResponseDTO:
    """Data transfer object for a chat response."""

    message: ChatMessageDTO
    session_id: uuid.UUID
    references: tuple[ChatMessageDTO, ...] = ()
    processing_time_ms: float = 0.0
    tokens_used: int = 0

    @property
    def has_references(self) -> bool:
        """Whether the response includes reference messages."""
        return len(self.references) > 0


@dataclass(frozen=True)
class ChatSessionDTO:
    """Data transfer object for a chat session."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    title: str = ""
    message_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_entity(cls, session: Any) -> ChatSessionDTO:
        """Create a DTO from a session entity."""
        return cls(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            message_count=session.message_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
