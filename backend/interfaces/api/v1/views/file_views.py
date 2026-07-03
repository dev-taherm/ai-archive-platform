from __future__ import annotations

import logging

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

    def list(self, request):
        offset = (int(request.query_params.get("page", 1)) - 1) * int(
            request.query_params.get("page_size", 20)
        )
        limit = int(request.query_params.get("page_size", 20))

        try:
            files = self._file_service.list_files(offset=offset, limit=limit)
            serializer = FileRecordSerializer(files, many=True)
            return Response(serializer.data)
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    def retrieve(self, request, pk=None):
        import uuid as _uuid
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
            return Response(
                {"detail": e.message}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
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
        import uuid as _uuid
        try:
            file_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid file ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_record = self._file_service.get_file(file_id)
            return Response(
                {"download_url": file_record.path},
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_404_NOT_FOUND
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
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_file(self, request, pk=None):
        import uuid as _uuid
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
            return Response(
                {"detail": e.message}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["patch"], url_path="rename")
    def rename(self, request, pk=None):
        import uuid as _uuid
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
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        import uuid as _uuid
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
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def copy(self, request, pk=None):
        import uuid as _uuid
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
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )
