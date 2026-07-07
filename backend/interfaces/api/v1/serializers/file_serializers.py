from __future__ import annotations

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
