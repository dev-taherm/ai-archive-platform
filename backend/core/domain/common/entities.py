from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class BaseEntity:
    """Base entity for all domain objects.

    Uses frozen dataclass for immutability. Entities are identified by UUID
    and track creation/modification timestamps.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def with_updated_timestamp(self) -> BaseEntity:
        """Return a new copy with updated_at set to now."""
        return self.__class__(
            **{
                **self.__dict__,
                "updated_at": datetime.now(timezone.utc),
            }
        )

    def __post_init__(self) -> None:
        if isinstance(self.id, str):
            object.__setattr__(self, "id", uuid.UUID(self.id))
        if isinstance(self.created_at, str):
            object.__setattr__(
                self, "created_at", datetime.fromisoformat(self.created_at)
            )
        if isinstance(self.updated_at, str):
            object.__setattr__(
                self, "updated_at", datetime.fromisoformat(self.updated_at)
            )
