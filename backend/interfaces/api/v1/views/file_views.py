from __future__ import annotations

import json
import logging
import time
import uuid as _uuid
from pathlib import Path

from django.http import StreamingHttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from interfaces.api.v1.serializers.file_serializers import (
    FileCopySerializer,
    FileDeleteSerializer,
    FileMoveSerializer,
    FileOperationSerializer,
    FileRecordSerializer,
    FileRenameSerializer,
    FileUploadSerializer,
    ScanFolderSerializer,
    ScanResultSerializer,
)

logger = logging.getLogger(__name__)


class FileRecordViewSet(viewsets.GenericViewSet):
    """
    ViewSet for file record management.

    Provides list, retrieve, upload, download, scan, delete, rename, move,
    and copy actions. Delegates all business logic to FileService.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action == "upload":
            return FileUploadSerializer
        if self.action == "scan":
            return ScanFolderSerializer
        if self.action == "rename":
            return FileRenameSerializer
        if self.action == "move":
            return FileMoveSerializer
        if self.action == "copy":
            return FileCopySerializer
        if self.action == "delete_file":
            return FileDeleteSerializer
        return FileRecordSerializer

    @property
    def _file_service(self):
        from django.apps import apps

        return apps.get_app_config("files").file_service

    @property
    def _file_use_cases(self):
        service = self._file_service
        return service._file_use_cases

    def list(self, request):
        try:
            files = self._file_service.list_files()
            page = self.paginate_queryset(files)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(files, many=True)
            return Response(serializer.data)
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        try:
            file_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid file ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_record = self._file_service.get_file(file_id)
            serializer = FileRecordSerializer(file_record)
            return Response(serializer.data)
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

    @action(
        detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser]
    )
    def upload(self, request):
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        tags = serializer.validated_data.get("tags", [])
        metadata = serializer.validated_data.get("metadata", {})

        try:
            from django.core.files.storage import default_storage

            path = default_storage.save(f"uploads/{uploaded_file.name}", uploaded_file)

            return Response(
                {
                    "message": "File uploaded successfully.",
                    "path": path,
                    "tags": tags,
                    "metadata": metadata,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.exception("File upload failed")
            return Response(
                {"detail": f"Upload failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        import mimetypes
        import os

        from django.http import FileResponse

        try:
            file_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid file ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_record = self._file_service.get_file(file_id)
            file_path = str(file_record.path)

            if not file_path or not os.path.exists(file_path):
                return Response(
                    {"detail": "File not found on disk."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            content_type = (
                mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            )
            filename = os.path.basename(file_path)

            response = FileResponse(
                open(file_path, "rb"),
                content_type=content_type,
            )
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("File download failed")
            return Response(
                {"detail": f"Download failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="scan")
    def scan(self, request):
        serializer = ScanFolderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self._file_service.scan_folder(
                folder_path=serializer.validated_data["folder_path"],
                user_id=request.user.pk if request.user.is_authenticated else None,
                recursive=serializer.validated_data.get("recursive", True),
                patterns=serializer.validated_data.get("patterns"),
                ignore_patterns=serializer.validated_data.get("ignore_patterns"),
            )
            return Response(
                ScanResultSerializer(result).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="scan-stream")
    def scan_stream(self, request):
        """SSE endpoint that streams scan progress as files are discovered and processed."""
        folder_path = request.query_params.get("folder_path", "").strip()
        if not folder_path:
            return Response(
                {"detail": "folder_path query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not folder_path.startswith("/"):
            return Response(
                {"detail": "Folder path must be an absolute path (starts with /)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        path_obj = Path(folder_path)
        if not path_obj.exists():
            return Response(
                {"detail": f"Folder path does not exist: {folder_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not path_obj.is_dir():
            return Response(
                {"detail": f"Path is not a directory: {folder_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recursive = request.query_params.get("recursive", "true").lower() == "true"

        def event_stream():
            def send_event(event_name: str, data: dict):
                yield f"event: {event_name}\ndata: {json.dumps(data)}\n\n"

            start_time = time.monotonic()
            processed = 0
            new_files = 0
            skipped = 0
            failed = 0
            total_found = 0
            errors = []

            yield from send_event(
                "scan_started",
                {
                    "message": "Scanning folder...",
                    "folder_path": folder_path,
                },
            )

            file_scanner = self._file_use_cases._file_scanner
            file_repository = self._file_use_cases._file_repository

            for file_info in file_scanner.scan_folder(folder_path, recursive=recursive):
                total_found += 1
                current_file = file_info.get("path", "unknown")
                processed += 1

                try:
                    from core.domain.files.entities import FileFingerprint, FileRecord
                    from core.domain.files.value_objects import (
                        FileSize,
                        FilePath,
                        FileStatus,
                        Hash,
                        MimeType,
                    )

                    content_hash_str = file_info.get("content_hash", "")
                    if ":" in content_hash_str:
                        algo, digest = content_hash_str.split(":", 1)
                    else:
                        algo, digest = "sha256", content_hash_str

                    content_hash = Hash(algorithm=algo, digest=digest)
                    file_size_obj = FileSize(bytes=file_info.get("size_bytes", 0))

                    existing = file_repository.get_by_fingerprint(content_hash)
                    if existing:
                        skipped += 1
                    else:
                        record = FileRecord(
                            path=FilePath(raw=file_info["path"]),
                            mime_type=MimeType(
                                value=file_info.get(
                                    "mime_type", "application/octet-stream"
                                )
                            ),
                            size=file_size_obj,
                            fingerprint=FileFingerprint(
                                content_hash=content_hash,
                                size=file_size_obj,
                                magic_bytes=file_info.get("magic_bytes", ""),
                            ),
                            status=FileStatus.PENDING,
                        )
                        file_repository.save(record)
                        new_files += 1

                except Exception as e:
                    failed += 1
                    errors.append(f"{current_file}: {e}")
                    logger.exception("Failed to process file: %s", current_file)

                yield from send_event(
                    "file_scanned",
                    {
                        "processed": processed,
                        "total_found": total_found,
                        "current_file": current_file,
                        "new": new_files,
                        "skipped": skipped,
                        "failed": failed,
                    },
                )

            duration = round(time.monotonic() - start_time, 3)

            yield from send_event(
                "scan_complete",
                {
                    "total_found": total_found,
                    "files_scanned": processed,
                    "new_files": new_files,
                    "skipped_files": skipped,
                    "failed_files": failed,
                    "scan_duration_seconds": duration,
                    "errors": errors,
                },
            )

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_file(self, request, pk=None):
        try:
            file_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid file ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self._file_service.delete_file(
                file_id,
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                FileOperationSerializer(result).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["patch"], url_path="rename")
    def rename(self, request, pk=None):
        try:
            file_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid file ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FileRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self._file_service.rename_file(
                file_id,
                new_name=serializer.validated_data["new_name"],
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                FileOperationSerializer(result).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        try:
            file_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid file ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FileMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self._file_service.move_file(
                file_id,
                destination_folder=serializer.validated_data["destination_folder"],
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                FileOperationSerializer(result).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def copy(self, request, pk=None):
        try:
            file_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid file ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FileCopySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self._file_service.copy_file(
                file_id,
                destination_folder=serializer.validated_data["destination_folder"],
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                FileOperationSerializer(result).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
