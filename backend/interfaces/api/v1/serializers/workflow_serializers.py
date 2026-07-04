from __future__ import annotations

import uuid as _uuid

from rest_framework import serializers


class WorkflowStepSerializer(serializers.Serializer):
    """Serializer for a workflow step stored in the JSONField."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True, default="pending")


class WorkflowSerializer(serializers.Serializer):
    """Serializer for workflow representation."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    trigger = serializers.CharField(source="trigger_type", read_only=True)
    steps = serializers.SerializerMethodField()
    last_run_at = serializers.DateTimeField(read_only=True, allow_null=True)
    next_run_at = serializers.SerializerMethodField()
    run_count = serializers.IntegerField(read_only=True, default=0)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_status(self, obj) -> str:
        if not obj.is_active:
            return "paused"
        last_run = getattr(obj, "_last_run", None)
        if last_run and last_run.status == "failed":
            return "failed"
        return "active"

    def get_steps(self, obj) -> list[dict]:
        raw_steps = obj.steps or []
        result = []
        for i, step in enumerate(raw_steps):
            result.append({
                "id": str(step.get("id", _uuid.uuid5(_uuid.NAMESPACE_URL, f"{obj.id}-step-{i}"))),
                "name": step.get("name", f"Step {i + 1}"),
                "type": step.get("type", step.get("step_type", "unknown")),
                "status": step.get("status", "pending"),
            })
        return result

    def get_next_run_at(self, obj) -> None:
        return None


class WorkflowCreateSerializer(serializers.Serializer):
    """Serializer for creating a new workflow."""

    name = serializers.CharField(max_length=256, min_length=1)
    description = serializers.CharField(
        max_length=2000, required=False, default=""
    )
    trigger_type = serializers.ChoiceField(
        choices=["manual", "on_upload", "scheduled"],
        default="manual",
    )
    steps = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class WorkflowUpdateSerializer(serializers.Serializer):
    """Serializer for updating a workflow."""

    name = serializers.CharField(max_length=256, min_length=1, required=False)
    description = serializers.CharField(max_length=2000, required=False)
    trigger_type = serializers.ChoiceField(
        choices=["manual", "on_upload", "scheduled"],
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    steps = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )


class WorkflowRunSerializer(serializers.Serializer):
    """Serializer for a workflow run."""

    id = serializers.UUIDField(read_only=True)
    workflow_id = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    input_data = serializers.DictField(read_only=True, default=dict)
    output_data = serializers.DictField(read_only=True, default=dict)
    current_step = serializers.IntegerField(read_only=True)
    total_steps = serializers.IntegerField(read_only=True)
    error_message = serializers.CharField(read_only=True, allow_blank=True)
    started_at = serializers.DateTimeField(read_only=True, allow_null=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_workflow_id(self, obj) -> str:
        return str(obj.workflow_id) if hasattr(obj, "workflow_id") else ""


class WorkflowRunCreateSerializer(serializers.Serializer):
    """Serializer for triggering a workflow run."""

    input_data = serializers.DictField(required=False, default=dict)
