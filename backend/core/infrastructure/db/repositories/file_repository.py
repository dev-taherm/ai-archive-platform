from __future__ import annotations

import uuid
from typing import Any, Sequence

from django.db.models import QuerySet

from core.application.interfaces.repositories import FileRepository
from core.domain.common.exceptions import EntityNotFound
from core.domain.files.entities import DuplicateGroup, FileFingerprint, FileRecord
from core.domain.files.value_objects import FileSize, FilePath, FileStatus, Hash, MimeType


class DjangoFileRepository(FileRepository):
    """Django ORM implementation of FileRepository ABC."""

    def __init__(self) -> None:
        from apps.files.models import FileRecord as FileRecordModel
        self._model = FileRecordModel

    def _qs(self) -> QuerySet:
        return self._model.objects.all()

    def _to_domain(self, obj: Any) -> FileRecord:
        raw_hash = obj.content_hash or ""
        if ":" in raw_hash:
            algo, digest = raw_hash.split(":", 1)
        else:
            algo, digest = "sha256", raw_hash

        return FileRecord(
            id=obj.id,
            path=FilePath(raw=obj.path),
            mime_type=MimeType(value=obj.mime_type),
            size=FileSize(bytes=obj.size_bytes),
            fingerprint=FileFingerprint(
                content_hash=Hash(algorithm=algo, digest=digest),
                size=FileSize(bytes=obj.size_bytes),
            ),
            status=FileStatus(obj.status),
            checksum=Hash(algorithm="sha256", digest=obj.checksum) if obj.checksum else None,
            tags=tuple(obj.tags) if obj.tags else (),
            metadata=dict(obj.metadata) if obj.metadata else {},
            duplicate_group_id=obj.duplicate_group_id,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    def _from_domain(self, entity: FileRecord) -> dict[str, Any]:
        return {
            "id": entity.id,
            "path": entity.path.raw,
            "mime_type": entity.mime_type.value,
            "size_bytes": entity.size.bytes,
            "content_hash": entity.fingerprint.content_hash.canonical,
            "status": entity.status.value,
            "checksum": entity.checksum.digest if entity.checksum else "",
            "tags": list(entity.tags),
            "metadata": entity.metadata,
            "duplicate_group_id": entity.duplicate_group_id,
        }

    def get_by_id(self, file_id: uuid.UUID) -> FileRecord | None:
        try:
            obj = self._qs().get(id=file_id)
            return self._to_domain(obj)
        except self._model.DoesNotExist:
            return None

    def save(self, file_record: FileRecord) -> FileRecord:
        data = self._from_domain(file_record)
        obj, _ = self._model.objects.update_or_create(
            id=file_record.id,
            defaults=data,
        )
        return self._to_domain(obj)

    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[FileRecord]:
        qs = self._qs().order_by("-created_at")[offset : offset + limit]
        return [self._to_domain(obj) for obj in qs]

    def delete(self, file_id: uuid.UUID) -> bool:
        deleted_count, _ = self._qs().filter(id=file_id).delete()
        return deleted_count > 0

    def get_by_fingerprint(self, fingerprint_hash: Hash) -> Sequence[FileRecord]:
        qs = self._qs().filter(content_hash=fingerprint_hash.canonical)
        return [self._to_domain(obj) for obj in qs]

    def find_duplicates(self) -> Sequence[dict[str, Any]]:
        from django.db.models import Count
        dup_qs = (
            self._qs()
            .values("content_hash")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1, content_hash__isnull=False)
            .exclude(content_hash="")
        )
        results: list[dict[str, Any]] = []
        for group in dup_qs:
            files_qs = self._qs().filter(content_hash=group["content_hash"])
            files = [self._to_domain(obj) for obj in files_qs]
            results.append({
                "fingerprint_hash": group["content_hash"],
                "file_count": group["cnt"],
                "files": files,
            })
        return results
