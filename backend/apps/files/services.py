from __future__ import annotations

import logging
import uuid

from core.application.dtos.file_dto import FileOperationDTO, FileRecordDTO, ScanResultDTO
from core.application.use_cases.file_use_cases import FileUseCases

logger = logging.getLogger(__name__)


class FileService:
    """Thin wrapper delegating file operations to core FileUseCases."""

    def __init__(self, file_use_cases: FileUseCases) -> None:
        self._file_use_cases = file_use_cases

    def scan_folder(
        self,
        folder_path: str,
        *,
        user_id: uuid.UUID | None = None,
        recursive: bool = True,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> ScanResultDTO:
        result = self._file_use_cases.scan_folder(
            folder_path,
            recursive=recursive,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
        )
        logger.info(
            "Folder scanned: %s — %d new files, %d skipped",
            folder_path,
            result.new_files,
            result.skipped_files,
        )
        return result

    def get_file(self, file_id: uuid.UUID) -> FileRecordDTO:
        return self._file_use_cases.get_file(file_id)

    def list_files(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[FileRecordDTO]:
        return self._file_use_cases.list_files(offset=offset, limit=limit)

    def delete_file(
        self,
        file_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        result = self._file_use_cases.delete_file(file_id)
        if result.success:
            logger.info("File deleted: %s", file_id)
        else:
            logger.warning("File deletion failed: %s — %s", file_id, result.error_message)
        return result

    def rename_file(
        self,
        file_id: uuid.UUID,
        new_name: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        return self._file_use_cases.rename_file(file_id, new_name)

    def move_file(
        self,
        file_id: uuid.UUID,
        destination_folder: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        return self._file_use_cases.move_file(file_id, destination_folder)

    def copy_file(
        self,
        file_id: uuid.UUID,
        destination_folder: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FileOperationDTO:
        return self._file_use_cases.copy_file(file_id, destination_folder)
