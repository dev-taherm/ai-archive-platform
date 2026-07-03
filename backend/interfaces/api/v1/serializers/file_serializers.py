from __future__ import annotations

import uuid

from rest_framework import serializers


class FileRecordSerializer(serializers.Serializer):
    """Serializer for file record representation."""

    id = serializers.UUIDField(read_only=True)
    path = serializers.CharField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    size_bytes = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    checksum = serializers.CharField(read_only=True, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(), read_only=True, default=list
    )
    metadata = serializers.DictField(read_only=True, default=dict)
    duplicate_group_id = serializers.UUIDField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests."""

    file = serializers.FileField()
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        max_length=50,
    )
    metadata = serializers.DictField(required=False, default=dict)

    def validate_tags(self, value: list[str]) -> list[str]:
        if len(value) > 50:
            raise serializers.ValidationError("A maximum of 50 tags is allowed.")
        return [tag.strip().lower() for tag in value]


class ScanFolderSerializer(serializers.Serializer):
    """Serializer for folder scan requests."""

    folder_path = serializers.CharField(
        max_length=1024,
        help_text="Absolute path to the folder to scan.",
    )
    recursive = serializers.BooleanField(default=True)
    patterns = serializers.ListField(
        child=serializers.CharField(max_length=256),
        required=False,
        default=None,
        allow_null=True,
        help_text="Glob patterns to include (e.g. ['*.pdf', '*.txt']).",
    )
    ignore_patterns = serializers.ListField(
        child=serializers.CharField(max_length=256),
        required=False,
        default=None,
        allow_null=True,
        help_text="Glob patterns to exclude.",
    )

    def validate_folder_path(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Folder path cannot be empty.")
        return value


class ScanResultSerializer(serializers.Serializer):
    """Serializer for folder scan results."""

    folder_path = serializers.CharField()
    total_files_found = serializers.IntegerField()
    files_scanned = serializers.IntegerField()
    new_files = serializers.IntegerField()
    skipped_files = serializers.IntegerField()
    failed_files = serializers.IntegerField()
    scan_duration_seconds = serializers.FloatField()
    scanned_at = serializers.DateTimeField()
    errors = serializers.ListField(child=serializers.CharField())
    file_ids = serializers.ListField(child=serializers.UUIDField())


class FileOperationSerializer(serializers.Serializer):
    """Serializer for file operation results (rename, move, copy, delete)."""

    operation = serializers.CharField()
    file_id = serializers.UUIDField()
    source_path = serializers.CharField()
    destination_path = serializers.CharField(allow_null=True)
    success = serializers.BooleanField()
    error_message = serializers.CharField(allow_null=True)
    performed_at = serializers.DateTimeField()


class FileRenameSerializer(serializers.Serializer):
    """Serializer for file rename requests."""

    new_name = serializers.CharField(max_length=256, min_length=1)

    def validate_new_name(self, value: str) -> str:
        value = value.strip()
        if "/" in value or "\\" in value:
            raise serializers.ValidationError(
                "New name must not contain path separators."
            )
        if not value:
            raise serializers.ValidationError("New name cannot be empty.")
        return value


class FileMoveSerializer(serializers.Serializer):
    """Serializer for file move requests."""

    destination_folder = serializers.CharField(max_length=1024)

    def validate_destination_folder(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Destination folder cannot be empty.")
        return value


class FileCopySerializer(serializers.Serializer):
    """Serializer for file copy requests."""

    destination_folder = serializers.CharField(max_length=1024)

    def validate_destination_folder(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Destination folder cannot be empty.")
        return value


class FileDeleteSerializer(serializers.Serializer):
    """Serializer for file delete confirmation."""

    file_id = serializers.UUIDField()
