from __future__ import annotations

from rest_framework import serializers


class ReportSummarySerializer(serializers.Serializer):
    """Serializer for the reports summary response shape."""

    storage = serializers.DictField(read_only=True)
    processing = serializers.DictField(read_only=True)
    activity = serializers.DictField(read_only=True)


class ReportSerializer(serializers.Serializer):
    """Serializer for a single report record."""

    id = serializers.UUIDField(read_only=True)
    report_type = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    parameters = serializers.DictField(read_only=True, default=dict)
    data = serializers.DictField(read_only=True, default=dict)
    file_path = serializers.CharField(read_only=True, allow_blank=True)
    error_message = serializers.CharField(read_only=True, allow_blank=True)
    generated_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class ReportCreateSerializer(serializers.Serializer):
    """Serializer for creating a new report."""

    report_type = serializers.ChoiceField(
        choices=[
            "archive_summary",
            "processing_stats",
            "search_analytics",
            "user_activity",
            "storage_usage",
            "custom",
        ]
    )
    title = serializers.CharField(max_length=255, min_length=1)
    parameters = serializers.DictField(required=False, default=dict)
