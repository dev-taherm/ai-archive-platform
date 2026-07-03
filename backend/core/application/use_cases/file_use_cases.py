from __future__ import annotations

import hashlib
import logging
import time
import uuid
from pathlib import PurePosixPath
from typing import AsyncIterator

from core.application.dtos.file_dto import FileOperationDTO, FileRecordDTO, ScanResultDTO
from core.application.interfaces.repositories import FileRepository
from core.application.interfaces.services import FileScanner, StorageBackend
from core.domain.common.exceptions import EntityNotFound, ValidationException
from core.domain.files.entities import FileFingerprint, FileRecord
from core.domain.files.value_objects import FileSize, FilePath, FileStatus, Hash, MimeType

logger = logging.getLogger(__name__)


class FileUseCases:
    """Use cases for file operations within the archive."""

    def __init__(
        self,
        file_repository: FileRepository,
        storage_backend: StorageBackend,
        file_scanner: FileScanner,
    ) -> None:
        self._file_repository = file_repository
        self._storage_backend = storage_backend
        self._file_scanner = file_scanner

    async def scan_folder(
        self,
        folder_path: str,
        *,
        recursive: bool = True,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> ScanResultDTO:
        """Scan a folder for files and register them in the archive."""
        total_found = 0
        scanned = 0
        new_files = 0
        skipped = 0
        failed = 0
        errors: list[str] = []
        file_ids: list[uuid.UUID] = []

        start_time = time.monotonic()

        async for file_info in self._file_scanner.scan_folder(
            folder_path,
            recursive=recursive,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
        ):
            total_found += 1
            try:
                file_path = file_info["path"]
                file_size = file_info.get("size_bytes", 0)
                mime_value = file_info.get("mime_type", "application/octet-stream")
                content_hash_str = file_info.get("content_hash", "")

                # Parse the content hash (format: "sha256:hexdigest")
                if ":" in content_hash_str:
                    algo, digest = content_hash_str.split(":", 1)
                else:
                    algo, digest = "sha256", content_hash_str

                content_hash = Hash(algorithm=algo, digest=digest)
                file_size_obj = FileSize(bytes=file_size)

                # Check for duplicates by fingerprint
                existing = await self._file_repository.get_by_fingerprint(content_hash)
                if existing:
                    skipped += 1
                    continue

                # Create domain entity
                record = FileRecord(
                    path=FilePath(raw=file_path),
                    mime_type=MimeType(value=mime_value),
                    size=file_size_obj,
                    fingerprint=FileFingerprint(
                        content_hash=content_hash,
                        size=file_size_obj,
                        magic_bytes=file_info.get("magic_bytes", ""),
                    ),
                    status=FileStatus.PENDING,
                )

                saved = await self._file_repository.save(record)
                file_ids.append(saved.id)
                new_files += 1
                scanned += 1

            except Exception as e:
                failed += 1
                errors.append(f"{file_info.get('path', 'unknown')}: {e}")
                logger.exception("Failed to scan file: %s", file_info.get("path"))

        duration = time.monotonic() - start_time

        return ScanResultDTO(
            folder_path=folder_path,
            total_files_found=total_found,
            files_scanned=scanned,
            new_files=new_files,
            skipped_files=skipped,
            failed_files=failed,
            scan_duration_seconds=round(duration, 3),
            errors=tuple(errors),
            file_ids=tuple(file_ids),
        )

    async def get_file(self, file_id: uuid.UUID) -> FileRecordDTO:
        """Retrieve a file record by ID."""
        record = await self._file_repository.get_by_id(file_id)
        if record is None:
            raise EntityNotFound("FileRecord", str(file_id))
        return FileRecordDTO.from_entity(record)

    async def list_files(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[FileRecordDTO]:
        """List all file records with pagination."""
        records = await self._file_repository.list_all(offset=offset, limit=limit)
        return [FileRecordDTO.from_entity(r) for r in records]

    async def delete_file(self, file_id: uuid.UUID) -> FileOperationDTO:
        """Delete a file from the archive and storage."""
        record = await self._file_repository.get_by_id(file_id)
        if record is None:
            raise EntityNotFound("FileRecord", str(file_id))

        source_path = record.path.normalized

        try:
            await self._storage_backend.delete(source_path)
        except Exception as e:
            logger.warning("Failed to delete from storage: %s", e)

        deleted = await self._file_repository.delete(file_id)
        if not deleted:
            return FileOperationDTO.failure_result(
                operation="delete",
                file_id=file_id,
                source_path=source_path,
                error_message="File record not found for deletion",
            )

        return FileOperationDTO.success_result(
            operation="delete",
            file_id=file_id,
            source_path=source_path,
        )

    async def rename_file(
        self,
        file_id: uuid.UUID,
        new_name: str,
    ) -> FileOperationDTO:
        """Rename a file within the archive."""
        record = await self._file_repository.get_by_id(file_id)
        if record is None:
            raise EntityNotFound("FileRecord", str(file_id))

        if not new_name.strip():
            raise ValidationException("New filename cannot be empty")

        old_path = record.path.normalized
        parent = PurePosixPath(old_path).parent
        new_full_path = str(parent / new_name)

        try:
            old_content = await self._storage_backend.retrieve(old_path)
            await self._storage_backend.save(new_full_path, old_content)
            await self._storage_backend.delete(old_path)
        except Exception as e:
            logger.exception("Failed to rename file in storage")
            return FileOperationDTO.failure_result(
                operation="rename",
                file_id=file_id,
                source_path=old_path,
                error_message=f"Storage rename failed: {e}",
            )

        new_path_obj = FilePath(raw=new_full_path)
        updated = FileRecord(
            id=record.id,
            path=new_path_obj,
            mime_type=record.mime_type,
            size=record.size,
            fingerprint=record.fingerprint,
            status=record.status,
            checksum=record.checksum,
            tags=record.tags,
            metadata=record.metadata,
            duplicate_group_id=record.duplicate_group_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        updated = updated.with_updated_timestamp()
        await self._file_repository.save(updated)

        return FileOperationDTO.success_result(
            operation="rename",
            file_id=file_id,
            source_path=old_path,
            destination_path=new_full_path,
        )

    async def move_file(
        self,
        file_id: uuid.UUID,
        destination_folder: str,
    ) -> FileOperationDTO:
        """Move a file to a different folder."""
        record = await self._file_repository.get_by_id(file_id)
        if record is None:
            raise EntityNotFound("FileRecord", str(file_id))

        old_path = record.path.normalized
        filename = PurePosixPath(old_path).name
        new_full_path = str(PurePosixPath(destination_folder) / filename)

        try:
            old_content = await self._storage_backend.retrieve(old_path)
            await self._storage_backend.save(new_full_path, old_content)
            await self._storage_backend.delete(old_path)
        except Exception as e:
            logger.exception("Failed to move file in storage")
            return FileOperationDTO.failure_result(
                operation="move",
                file_id=file_id,
                source_path=old_path,
                error_message=f"Storage move failed: {e}",
            )

        new_path_obj = FilePath(raw=new_full_path)
        updated = FileRecord(
            id=record.id,
            path=new_path_obj,
            mime_type=record.mime_type,
            size=record.size,
            fingerprint=record.fingerprint,
            status=record.status,
            checksum=record.checksum,
            tags=record.tags,
            metadata=record.metadata,
            duplicate_group_id=record.duplicate_group_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        updated = updated.with_updated_timestamp()
        await self._file_repository.save(updated)

        return FileOperationDTO.success_result(
            operation="move",
            file_id=file_id,
            source_path=old_path,
            destination_path=new_full_path,
        )

    async def copy_file(
        self,
        file_id: uuid.UUID,
        destination_folder: str,
    ) -> FileOperationDTO:
        """Copy a file to a different folder."""
        record = await self._file_repository.get_by_id(file_id)
        if record is None:
            raise EntityNotFound("FileRecord", str(file_id))

        source_path = record.path.normalized
        filename = PurePosixPath(source_path).name
        dest_full_path = str(PurePosixPath(destination_folder) / filename)

        try:
            content = await self._storage_backend.retrieve(source_path)
            await self._storage_backend.save(dest_full_path, content)
        except Exception as e:
            logger.exception("Failed to copy file in storage")
            return FileOperationDTO.failure_result(
                operation="copy",
                file_id=file_id,
                source_path=source_path,
                error_message=f"Storage copy failed: {e}",
            )

        new_path_obj = FilePath(raw=dest_full_path)
        fingerprint = FileFingerprint(
            content_hash=record.fingerprint.content_hash,
            size=record.size,
            magic_bytes=record.fingerprint.magic_bytes,
            extra=record.fingerprint.extra,
        )
        copy_record = FileRecord(
            path=new_path_obj,
            mime_type=record.mime_type,
            size=record.size,
            fingerprint=fingerprint,
            status=FileStatus.PENDING,
            checksum=record.checksum,
            tags=list(record.tags),
            metadata=dict(record.metadata),
        )
        saved_copy = await self._file_repository.save(copy_record)

        return FileOperationDTO.success_result(
            operation="copy",
            file_id=saved_copy.id,
            source_path=source_path,
            destination_path=dest_full_path,
        )
