from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Timestamp:
    """Immutable value object wrapping a UTC datetime with convenience methods."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            object.__setattr__(self, "value", self.value.replace(tzinfo=timezone.utc))

    @classmethod
    def now(cls) -> Timestamp:
        return cls(value=datetime.now(timezone.utc))

    @classmethod
    def fromisoformat(cls, iso_string: str) -> Timestamp:
        return cls(value=datetime.fromisoformat(iso_string))

    @property
    def isoformat(self) -> str:
        return self.value.isoformat()

    @property
    def epoch_seconds(self) -> float:
        return self.value.timestamp()

    def __gt__(self, other: Timestamp) -> bool:
        return self.value > other.value

    def __ge__(self, other: Timestamp) -> bool:
        return self.value >= other.value

    def __lt__(self, other: Timestamp) -> bool:
        return self.value < other.value

    def __le__(self, other: Timestamp) -> bool:
        return self.value <= other.value


@dataclass(frozen=True)
class EntityId:
    """Immutable value object wrapping a UUID for domain entity identification."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if isinstance(self.value, str):
            object.__setattr__(self, "value", uuid.UUID(self.value))

    @classmethod
    def generate(cls) -> EntityId:
        return cls(value=uuid.uuid4())

    @classmethod
    def from_string(cls, raw: str) -> EntityId:
        return cls(value=uuid.UUID(raw))

    @property
    def hex(self) -> str:
        return self.value.hex

    @property
    def short(self) -> str:
        return self.value.hex[:8]
