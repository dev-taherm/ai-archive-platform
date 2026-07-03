from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class FileRecordDTO:
    """Data transfer object for file record information."""

    id: uuid.UUID
    path: str
    mime_type: str
    size_bytes: int
    status: str
    checksum: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    duplicate_group_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_entity(cls, file_record: Any) -> FileRecordDTO:
        """Create a DTO from a FileRecord domain entity."""
        return cls(
            id=file_record.id,
            path=file_record.path.normalized,
            mime_type=file_record.mime_type.value,
            size_bytes=file_record.size.bytes,
            status=file_record.status.value,
            checksum=file_record.checksum.canonical if file_record.checksum else None,
            tags=tuple(file_record.tags),
            metadata=file_record.metadata,
            duplicate_group_id=file_record.duplicate_group_id,
            created_at=file_record.created_at,
            updated_at=file_record.updated_at,
        )


@dataclass(frozen=True)
class ScanResultDTO:
    """Data transfer object for folder scan results."""

    folder_path: str
    total_files_found: int
    files_scanned: int
    new_files: int
    skipped_files: int
    failed_files: int
    scan_duration_seconds: float
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: tuple[str, ...] = ()
    file_ids: tuple[uuid.UUID, ...] = ()


@dataclass(frozen=True)
class FileOperationDTO:
    """Data transfer object for file operation results."""

    operation: str
    file_id: uuid.UUID
    source_path: str
    destination_path: str | None = None
    success: bool = True
    error_message: str | None = None
    performed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def success_result(
        cls,
        operation: str,
        file_id: uuid.UUID,
        source_path: str,
        destination_path: str | None = None,
    ) -> FileOperationDTO:
        """Create a successful operation result."""
        return cls(
            operation=operation,
            file_id=file_id,
            source_path=source_path,
            destination_path=destination_path,
            success=True,
        )

    @classmethod
    def failure_result(
        cls,
        operation: str,
        file_id: uuid.UUID,
        source_path: str,
        error_message: str,
    ) -> FileOperationDTO:
        """Create a failed operation result."""
        return cls(
            operation=operation,
            file_id=file_id,
            source_path=source_path,
            success=False,
            error_message=error_message,
        )
