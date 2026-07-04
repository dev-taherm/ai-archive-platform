from __future__ import annotations

import uuid
from typing import Any, Sequence

from django.db.models import Count

from apps.files.models import FileRecord as DjangoFileRecord
from core.application.interfaces.repositories import FileRepository
from core.domain.files.entities import FileFingerprint, FileRecord
from core.domain.files.value_objects import (
    FileSize,
    FilePath,
    FileStatus,
    Hash,
    MimeType,
)


class DjangoFileRepository(FileRepository):
    """Django ORM implementation of the FileRepository interface."""

    def get_by_id(self, file_id: uuid.UUID) -> FileRecord | None:
        try:
            orm = DjangoFileRecord.objects.get(pk=file_id)
            return self._to_entity(orm)
        except DjangoFileRecord.DoesNotExist:
            return None

    def save(self, file_record: FileRecord) -> FileRecord:
        orm = self._to_orm(file_record)
        orm.save()
        return self._to_entity(orm)

    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[FileRecord]:
        qs = DjangoFileRecord.objects.all().order_by("-created_at")[offset : offset + limit]
        return [self._to_entity(orm) for orm in qs]

    def delete(self, file_id: uuid.UUID) -> bool:
        deleted, _ = DjangoFileRecord.objects.filter(pk=file_id).delete()
        return deleted > 0

    def get_by_fingerprint(self, fingerprint_hash: Hash) -> Sequence[FileRecord]:
        qs = DjangoFileRecord.objects.filter(content_hash=fingerprint_hash.digest)
        return [self._to_entity(orm) for orm in qs]

    def find_duplicates(self) -> Sequence[dict[str, Any]]:
        duplicate_hashes = (
            DjangoFileRecord.objects.values("content_hash")
            .annotate(file_count=Count("id"))
            .filter(file_count__gt=1, content_hash__gt="")
        )
        results = []
        for row in duplicate_hashes:
            file_ids = list(
                DjangoFileRecord.objects.filter(
                    content_hash=row["content_hash"]
                ).values_list("id", flat=True)
            )
            results.append(
                {
                    "hash": row["content_hash"],
                    "count": row["file_count"],
                    "file_ids": file_ids,
                }
            )
        return results

    @staticmethod
    def _to_entity(orm: DjangoFileRecord) -> FileRecord:
        return FileRecord(
            id=orm.id,
            path=FilePath(raw=orm.path),
            mime_type=MimeType(value=orm.mime_type),
            size=FileSize(bytes=orm.size_bytes),
            fingerprint=FileFingerprint(
                content_hash=Hash(algorithm="sha256", digest=orm.content_hash),
                size=FileSize(bytes=orm.size_bytes),
            ),
            status=FileStatus(orm.status),
            checksum=Hash(algorithm="sha256", digest=orm.checksum) if orm.checksum else None,
            tags=tuple(orm.tags),
            metadata=orm.metadata,
            duplicate_group_id=orm.duplicate_group_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _to_orm(entity: FileRecord) -> DjangoFileRecord:
        return DjangoFileRecord(
            id=entity.id,
            path=entity.path.raw,
            mime_type=entity.mime_type.value,
            size_bytes=entity.size.bytes,
            status=entity.status.value,
            content_hash=entity.fingerprint.content_hash.digest,
            checksum=entity.checksum.digest if entity.checksum else "",
            tags=list(entity.tags),
            metadata=entity.metadata,
            duplicate_group_id=entity.duplicate_group_id,
        )
