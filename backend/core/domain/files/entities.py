from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.domain.common.entities import BaseEntity
from core.domain.files.value_objects import FileSize, FilePath, FileStatus, Hash, MimeType


@dataclass(frozen=True)
class FileFingerprint:
    """Composite fingerprint for deduplication."""

    content_hash: Hash
    size: FileSize
    magic_bytes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileFingerprint):
            return NotImplemented
        return self.content_hash == other.content_hash

    def __hash__(self) -> int:
        return hash(self.content_hash)


@dataclass(frozen=True)
class FileRecord(BaseEntity):
    """Core file entity representing an archived file."""

    path: FilePath = field(default_factory=lambda: FilePath(raw="/"))
    mime_type: MimeType = field(default_factory=lambda: MimeType(value="application/octet-stream"))
    size: FileSize = field(default_factory=FileSize)
    fingerprint: FileFingerprint = field(default_factory=lambda: FileFingerprint(
        content_hash=Hash(algorithm="sha256", digest=""),
        size=FileSize(bytes=0),
    ))
    status: FileStatus = FileStatus.PENDING
    checksum: Hash | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    duplicate_group_id: uuid.UUID | None = None

    def mark_indexed(self) -> None:
        self.status = FileStatus.INDEXED
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def mark_duplicate(self, group_id: uuid.UUID) -> None:
        self.status = FileStatus.DUPLICATE
        object.__setattr__(self, "duplicate_group_id", group_id)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def mark_failed(self) -> None:
        self.status = FileStatus.FAILED
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def mark_deleted(self) -> None:
        self.status = FileStatus.DELETED
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    @property
    def is_available(self) -> bool:
        return self.status in (FileStatus.INDEXED, FileStatus.DUPLICATE)

    @property
    def extension(self) -> str:
        return self.path.extension

    @property
    def filename(self) -> str:
        return self.path.filename


@dataclass(frozen=True)
class DuplicateGroup:
    """Groups files that share the same content fingerprint."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    fingerprint: FileFingerprint | None = None
    file_ids: tuple[uuid.UUID, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False

    @property
    def file_count(self) -> int:
        return len(self.file_ids)

    def resolve(self) -> DuplicateGroup:
        """Return a new resolved copy."""
        return DuplicateGroup(
            id=self.id,
            fingerprint=self.fingerprint,
            file_ids=self.file_ids,
            created_at=self.created_at,
            resolved=True,
        )
