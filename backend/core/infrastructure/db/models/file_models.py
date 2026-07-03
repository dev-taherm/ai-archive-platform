from __future__ import annotations

import uuid
from typing import Any

from django.db import models

from core.domain.files.entities import DuplicateGroup, FileFingerprint, FileRecord
from core.domain.files.value_objects import (
    FileSize,
    FilePath,
    FileStatus,
    Hash,
    MimeType,
)
from core.infrastructure.db.models.base import BaseModel


class FileRecordModel(BaseModel):
    """Django ORM model for FileRecord domain entity."""

    path = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=127)
    size_bytes = models.BigIntegerField()
    content_hash_algorithm = models.CharField(max_length=31, default="sha256")
    content_hash_digest = models.CharField(max_length=127)
    magic_bytes = models.CharField(max_length=31, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in FileStatus],
        default=FileStatus.PENDING.value,
        db_index=True,
    )
    checksum = models.CharField(max_length=255, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    duplicate_group_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "file_record"
        indexes = [
            models.Index(fields=["status"], name="idx_file_status"),
            models.Index(fields=["content_hash_digest"], name="idx_file_hash"),
            models.Index(fields=["path"], name="idx_file_path"),
        ]

    def __str__(self) -> str:
        return f"FileRecord({self.path})"

    def to_domain(self) -> FileRecord:
        return FileRecord(
            id=self.id,
            path=FilePath(raw=self.path),
            mime_type=MimeType(value=self.mime_type),
            size=FileSize(bytes=self.size_bytes),
            fingerprint=FileFingerprint(
                content_hash=Hash(
                    algorithm=self.content_hash_algorithm,
                    digest=self.content_hash_digest,
                ),
                size=FileSize(bytes=self.size_bytes),
                magic_bytes=self.magic_bytes,
            ),
            status=FileStatus(self.status),
            checksum=Hash(canonical=self.checksum) if self.checksum else None,
            tags=list(self.tags) if self.tags else [],
            metadata=dict(self.metadata) if self.metadata else {},
            duplicate_group_id=self.duplicate_group_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: FileRecord) -> FileRecordModel:
        return cls(
            id=entity.id,
            path=entity.path.raw,
            mime_type=entity.mime_type.value,
            size_bytes=entity.size.bytes,
            content_hash_algorithm=entity.fingerprint.content_hash.algorithm,
            content_hash_digest=entity.fingerprint.content_hash.digest,
            magic_bytes=entity.fingerprint.magic_bytes,
            status=entity.status.value,
            checksum=entity.checksum.canonical if entity.checksum else None,
            tags=entity.tags,
            metadata=entity.metadata,
            duplicate_group_id=entity.duplicate_group_id,
        )


class FileFingerprintModel(BaseModel):
    """Django ORM model for FileFingerprint value object.

    Stored separately to enable efficient dedup lookups by composite key.
    """

    content_hash_algorithm = models.CharField(max_length=31)
    content_hash_digest = models.CharField(max_length=127)
    size_bytes = models.BigIntegerField()
    magic_bytes = models.CharField(max_length=31, blank=True, default="")
    extra = models.JSONField(default=dict, blank=True)
    file_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "file_fingerprint"
        indexes = [
            models.Index(
                fields=["content_hash_algorithm", "content_hash_digest"],
                name="idx_fingerprint_hash",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["content_hash_algorithm", "content_hash_digest"],
                name="uq_fingerprint_hash",
            ),
        ]

    def __str__(self) -> str:
        return f"Fingerprint({self.content_hash_algorithm}:{self.content_hash_digest[:16]}…)"

    def to_domain(self) -> FileFingerprint:
        return FileFingerprint(
            content_hash=Hash(
                algorithm=self.content_hash_algorithm,
                digest=self.content_hash_digest,
            ),
            size=FileSize(bytes=self.size_bytes),
            magic_bytes=self.magic_bytes,
            extra=dict(self.extra) if self.extra else {},
        )

    @classmethod
    def from_domain(cls, fp: FileFingerprint) -> FileFingerprintModel:
        return cls(
            content_hash_algorithm=fp.content_hash.algorithm,
            content_hash_digest=fp.content_hash.digest,
            size_bytes=fp.size.bytes,
            magic_bytes=fp.magic_bytes,
            extra=fp.extra,
        )


class DuplicateGroupModel(BaseModel):
    """Django ORM model for DuplicateGroup domain entity."""

    fingerprint_hash = models.CharField(max_length=255, db_index=True)
    file_ids = models.JSONField(default=list, blank=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "duplicate_group"
        indexes = [
            models.Index(fields=["resolved"], name="idx_dup_resolved"),
        ]

    def __str__(self) -> str:
        return f"DuplicateGroup({self.fingerprint_hash[:16]}…, files={len(self.file_ids)})"

    def to_domain(self) -> DuplicateGroup:
        return DuplicateGroup(
            id=self.id,
            fingerprint=None,
            file_ids=tuple(uuid.UUID(fid) for fid in self.file_ids) if self.file_ids else (),
            created_at=self.created_at,
            resolved=self.resolved,
        )

    @classmethod
    def from_domain(cls, entity: DuplicateGroup, fingerprint_hash: str = "") -> DuplicateGroupModel:
        return cls(
            id=entity.id,
            fingerprint_hash=fingerprint_hash,
            file_ids=[str(fid) for fid in entity.file_ids],
            resolved=entity.resolved,
        )
