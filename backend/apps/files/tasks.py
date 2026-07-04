from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="files.scan_folder_task")
def scan_folder_task(
    folder_path: str,
    recursive: bool = True,
    patterns: list[str] | None = None,
    ignore_patterns: list[str] | None = None,
) -> dict[str, object]:
    """Celery task to scan a folder asynchronously."""
    import asyncio

    from apps.files.services import FileService
    from core.application.use_cases.file_use_cases import FileUseCases

    async def _run() -> dict[str, object]:
        from core.infrastructure.db.repositories.file_repository import (
            DjangoFileRepository,
        )
        from core.infrastructure.services.file_scanner import FileScannerService
        from core.infrastructure.storage.local import LocalStorage

        repo = DjangoFileRepository()
        scanner = FileScannerService()
        storage = LocalStorage(root_dir="/tmp/archive-storage")
        use_cases = FileUseCases(repo, storage, scanner)
        service = FileService(use_cases)

        result = await service.scan_folder(
            folder_path,
            recursive=recursive,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
        )
        return {
            "folder_path": result.folder_path,
            "new_files": result.new_files,
            "total_found": result.total_files_found,
            "skipped": result.skipped_files,
            "failed": result.failed_files,
        }

    return asyncio.run(_run())


@shared_task(name="files.delete_file_task")
def delete_file_task(file_id: str) -> dict[str, object]:
    """Celery task to delete a file asynchronously."""
    import asyncio

    from apps.files.services import FileService
    from core.application.use_cases.file_use_cases import FileUseCases

    async def _run() -> dict[str, object]:
        from core.infrastructure.db.repositories.file_repository import (
            DjangoFileRepository,
        )
        from core.infrastructure.services.file_scanner import FileScannerService
        from core.infrastructure.storage.local import LocalStorage

        repo = DjangoFileRepository()
        scanner = FileScannerService()
        storage = LocalStorage(root_dir="/tmp/archive-storage")
        use_cases = FileUseCases(repo, storage, scanner)
        service = FileService(use_cases)

        result = await service.delete_file(uuid.UUID(file_id))
        return {"success": result.success, "error": result.error_message}

    return asyncio.run(_run())
