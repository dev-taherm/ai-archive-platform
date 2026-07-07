from __future__ import annotations

from rest_framework import serializers


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics overview."""

    total_files = serializers.IntegerField(read_only=True)
    total_documents = serializers.IntegerField(read_only=True)
    total_searches = serializers.IntegerField(read_only=True)
    total_chat_sessions = serializers.IntegerField(read_only=True)
    files_by_status = serializers.DictField(
        child=serializers.IntegerField(), read_only=True
    )
    documents_by_type = serializers.DictField(
        child=serializers.IntegerField(), read_only=True
    )
    documents_by_status = serializers.DictField(
        child=serializers.IntegerField(), read_only=True
    )
    recent_uploads_count = serializers.IntegerField(
        read_only=True,
        help_text="Number of files uploaded in the last 24 hours.",
    )
    storage_used_bytes = serializers.IntegerField(read_only=True)
    avg_processing_time_ms = serializers.FloatField(read_only=True)
    agents_total = serializers.IntegerField(read_only=True)
    agents_online = serializers.IntegerField(read_only=True)
    duplicate_files = serializers.IntegerField(read_only=True)
    duplicate_groups = serializers.IntegerField(read_only=True)


class ChartDataPointSerializer(serializers.Serializer):
    """Serializer for a single chart data point."""

    label = serializers.CharField()
    value = serializers.FloatField()
    count = serializers.IntegerField(required=False)


class ChartDataSerializer(serializers.Serializer):
    """Serializer for chart data used in dashboard visualizations."""

    chart_type = serializers.ChoiceField(
        choices=["line", "bar", "pie", "area"],
        read_only=True,
    )
    title = serializers.CharField(read_only=True)
    data = ChartDataPointSerializer(many=True, read_only=True)
    period = serializers.CharField(
        read_only=True,
        help_text="Time period the chart covers (e.g. '7d', '30d').",
    )


class ActivitySerializer(serializers.Serializer):
    """Serializer for a single activity log entry."""

    id = serializers.UUIDField(read_only=True)
    action = serializers.CharField(read_only=True)
    resource_type = serializers.CharField(read_only=True)
    resource_id = serializers.UUIDField(read_only=True, allow_null=True)
    user_email = serializers.EmailField(read_only=True, allow_null=True)
    details = serializers.DictField(read_only=True, default=dict)
    created_at = serializers.DateTimeField(read_only=True)


class ActivityListSerializer(serializers.Serializer):
    """Serializer for paginated activity list."""

    activities = ActivitySerializer(many=True, read_only=True)
    total_count = serializers.IntegerField(read_only=True)
