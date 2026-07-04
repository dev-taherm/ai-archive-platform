from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from core.domain.common.events import DomainEvent


@dataclass(frozen=True)
class FileCreated(DomainEvent):
    """Emitted when a new file is added to the archive."""

    file_id: uuid.UUID = field(default_factory=uuid.uuid4)
    path: str = ""
    mime_type: str = ""

    def __init__(self, file_id: uuid.UUID, path: str, mime_type: str) -> None:
        super().__init__(
            event_type="file.created",
            payload={
                "file_id": str(file_id),
                "path": path,
                "mime_type": mime_type,
            },
        )
        object.__setattr__(self, "file_id", file_id)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "mime_type", mime_type)


@dataclass(frozen=True)
class FileModified(DomainEvent):
    """Emitted when an existing file is modified."""

    file_id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __init__(self, file_id: uuid.UUID) -> None:
        super().__init__(
            event_type="file.modified",
            payload={"file_id": str(file_id)},
        )
        object.__setattr__(self, "file_id", file_id)


@dataclass(frozen=True)
class FileDeleted(DomainEvent):
    """Emitted when a file is removed from the archive."""

    file_id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __init__(self, file_id: uuid.UUID) -> None:
        super().__init__(
            event_type="file.deleted",
            payload={"file_id": str(file_id)},
        )
        object.__setattr__(self, "file_id", file_id)


@dataclass(frozen=True)
class FileDuplicateDetected(DomainEvent):
    """Emitted when a duplicate file is detected."""

    file_id: uuid.UUID = field(default_factory=uuid.uuid4)
    duplicate_group_id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __init__(self, file_id: uuid.UUID, duplicate_group_id: uuid.UUID) -> None:
        super().__init__(
            event_type="file.duplicate_detected",
            payload={
                "file_id": str(file_id),
                "duplicate_group_id": str(duplicate_group_id),
            },
        )
        object.__setattr__(self, "file_id", file_id)
        object.__setattr__(self, "duplicate_group_id", duplicate_group_id)
