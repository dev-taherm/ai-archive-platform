from __future__ import annotations

from rest_framework import serializers


class WorkflowStepSerializer(serializers.Serializer):
    """Serializer for a workflow step."""

    id = serializers.UUIDField(read_only=True)
    workflow_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    step_type = serializers.CharField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    config = serializers.DictField(read_only=True, default=dict)
    is_optional = serializers.BooleanField(read_only=True, default=False)
    timeout_seconds = serializers.IntegerField(read_only=True, default=300)
    retry_count = serializers.IntegerField(read_only=True, default=0)
    max_retries = serializers.IntegerField(read_only=True, default=3)
    dependencies = serializers.ListField(
        child=serializers.UUIDField(), read_only=True, default=list
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class WorkflowStepCreateSerializer(serializers.Serializer):
    """Serializer for creating a workflow step."""

    name = serializers.CharField(max_length=256, min_length=1)
    step_type = serializers.CharField(max_length=100)
    order = serializers.IntegerField(min_value=0, default=0)
    config = serializers.DictField(required=False, default=dict)
    is_optional = serializers.BooleanField(default=False)
    timeout_seconds = serializers.IntegerField(default=300, min_value=1)
    max_retries = serializers.IntegerField(default=3, min_value=0, max_value=10)
    dependencies = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


class WorkflowSerializer(serializers.Serializer):
    """Serializer for workflow representation."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    trigger_type = serializers.CharField(read_only=True)
    trigger_config = serializers.DictField(read_only=True, default=dict)
    steps = WorkflowStepSerializer(many=True, read_only=True, default=list)
    tags = serializers.ListField(
        child=serializers.CharField(), read_only=True, default=list
    )
    run_count = serializers.IntegerField(read_only=True)
    last_run_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class WorkflowCreateSerializer(serializers.Serializer):
    """Serializer for creating a new workflow."""

    name = serializers.CharField(max_length=256, min_length=1)
    description = serializers.CharField(
        max_length=2000, required=False, default=""
    )
    trigger_type = serializers.ChoiceField(
        choices=["manual", "scheduled", "event", "file_created", "file_modified", "api_webhook"],
        default="manual",
    )
    trigger_config = serializers.DictField(required=False, default=dict)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        max_length=20,
    )
    steps = WorkflowStepCreateSerializer(many=True, required=False, default=list)


class WorkflowUpdateSerializer(serializers.Serializer):
    """Serializer for updating a workflow."""

    name = serializers.CharField(max_length=256, min_length=1, required=False)
    description = serializers.CharField(
        max_length=2000, required=False
    )
    status = serializers.ChoiceField(
        choices=["draft", "active", "paused", "cancelled"],
        required=False,
    )
    trigger_type = serializers.ChoiceField(
        choices=["manual", "scheduled", "event", "file_created", "file_modified", "api_webhook"],
        required=False,
    )
    trigger_config = serializers.DictField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        max_length=20,
    )


class WorkflowRunSerializer(serializers.Serializer):
    """Serializer for a workflow run."""

    id = serializers.UUIDField(read_only=True)
    workflow_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    triggered_by = serializers.CharField(read_only=True)
    trigger_user_id = serializers.UUIDField(read_only=True, allow_null=True)
    input_data = serializers.DictField(read_only=True, default=dict)
    output_data = serializers.DictField(read_only=True, default=dict)
    step_results = serializers.DictField(read_only=True, default=dict)
    current_step_id = serializers.UUIDField(read_only=True, allow_null=True)
    error_message = serializers.CharField(read_only=True, allow_null=True)
    started_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    duration_ms = serializers.FloatField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class WorkflowRunCreateSerializer(serializers.Serializer):
    """Serializer for triggering a workflow run."""

    input_data = serializers.DictField(required=False, default=dict)
