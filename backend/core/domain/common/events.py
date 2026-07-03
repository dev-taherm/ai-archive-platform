from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    Events represent something meaningful that happened in the domain.
    They are immutable records carrying event_type, timestamp, and payload.
    """

    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, event_type: str, **payload: Any) -> DomainEvent:
        """Factory method to create a domain event with a payload."""
        return cls(event_type=event_type, payload=payload)

    def __post_init__(self) -> None:
        if isinstance(self.event_id, str):
            object.__setattr__(self, "event_id", uuid.UUID(self.event_id))
        if isinstance(self.timestamp, str):
            object.__setattr__(
                self, "timestamp", datetime.fromisoformat(self.timestamp)
            )
