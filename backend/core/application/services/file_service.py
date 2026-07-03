from __future__ import annotations

import logging
import uuid
from typing import Any

from core.application.dtos.file_dto import FileOperationDTO, FileRecordDTO, ScanResultDTO
from core.application.interfaces.repositories import (
    AuditLogRepository,
    FileRepository,
)
from core.application.interfaces.services import FileScanner, StorageBackend
from core.application.use_cases.file_use_cases import FileUseCases
from core.domain.common.exceptions import EntityNotFound, ValidationException

logger = logging.getLogger(__name__)


class FileService:
    """Application service orchestrating file operations with audit logging."""

    def __init__(
        self,
        file_use_cases: FileUseCases,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._file_use_cases = file_use_cases
        self._audit_log_repository = audit_log_repository

    async def scan_folder(
        self,
        folder_path: str,
        *,
        user_id: uuid.UUID | None = None,
        recursive: bool = True,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> ScanResultDTO:
        """Scan a folder and register new files, logging the operation."""
        result = await self._file_use_cases.scan_folder(
            folder_path,
            recursive=recursive,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
        )

        await self._audit(
            action="folder.scanned",
            user_id=user_id,
            resource_type="folder",
            resource_id=None,
            details={
                "folder_path": folder_path,
                "new_files": result.new_files,
                "total_found": result.total_files_found,
            },
        )

        return result

    async def get_file(
        self,
        file_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileRecordDTO:
        """Retrieve a file record by ID."""
        return await self._file_use_cases.get_file(file_id)

    async def list_files(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[FileRecordDTO]:
        """List all file records with pagination."""
        return await self._file_use_cases.list_files(offset=offset, limit=limit)

    async def delete_file(
        self,
        file_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        """Delete a file and log the operation."""
        result = await self._file_use_cases.delete_file(file_id)

        await self._audit(
            action="file.deleted",
            user_id=user_id,
            resource_type="file",
            resource_id=file_id,
            details={"success": result.success, "source_path": result.source_path},
        )

        return result

    async def rename_file(
        self,
        file_id: uuid.UUID,
        new_name: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        """Rename a file and log the operation."""
        result = await self._file_use_cases.rename_file(file_id, new_name)

        await self._audit(
            action="file.renamed",
            user_id=user_id,
            resource_type="file",
            resource_id=file_id,
            details={
                "new_name": new_name,
                "success": result.success,
                "source_path": result.source_path,
                "destination_path": result.destination_path,
            },
        )

        return result

    async def move_file(
        self,
        file_id: uuid.UUID,
        destination_folder: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        """Move a file to a different folder and log the operation."""
        result = await self._file_use_cases.move_file(file_id, destination_folder)

        await self._audit(
            action="file.moved",
            user_id=user_id,
            resource_type="file",
            resource_id=file_id,
            details={
                "destination_folder": destination_folder,
                "success": result.success,
                "source_path": result.source_path,
            },
        )

        return result

    async def copy_file(
        self,
        file_id: uuid.UUID,
        destination_folder: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        """Copy a file to a different folder and log the operation."""
        result = await self._file_use_cases.copy_file(file_id, destination_folder)

        await self._audit(
            action="file.copied",
            user_id=user_id,
            resource_type="file",
            resource_id=file_id,
            details={
                "destination_folder": destination_folder,
                "success": result.success,
                "source_path": result.source_path,
                "destination_path": result.destination_path,
            },
        )

        return result

    async def _audit(
        self,
        action: str,
        user_id: uuid.UUID | None,
        resource_type: str,
        resource_id: uuid.UUID | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Persist an audit log entry."""
        try:
            await self._audit_log_repository.save({
                "action": action,
                "user_id": str(user_id) if user_id else None,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "details": details or {},
            })
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)
