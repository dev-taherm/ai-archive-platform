from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Workflow(models.Model):
    """Defines a reusable processing workflow pipeline."""

    class TriggerType(models.TextChoices):
        MANUAL = "manual", "Manual"
        ON_UPLOAD = "on_upload", "On Upload"
        SCHEDULED = "scheduled", "Scheduled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="workflows",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    trigger_type = models.CharField(
        max_length=20,
        choices=TriggerType.choices,
        default=TriggerType.MANUAL,
    )
    steps = models.JSONField(
        default=list,
        help_text="Ordered list of step definitions for the workflow.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_workflows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflows_workflow"
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"
        indexes = [
            models.Index(fields=["is_active"], name="idx_workflow_active"),
            models.Index(fields=["trigger_type"], name="idx_workflow_trigger"),
        ]

    def __str__(self) -> str:
        return self.name


class WorkflowRun(models.Model):
    """Tracks individual executions of a workflow."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="workflow_runs",
        null=True,
        blank=True,
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    current_step = models.PositiveIntegerField(default=0)
    total_steps = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflows_workflowrun"
        verbose_name = "Workflow Run"
        verbose_name_plural = "Workflow Runs"
        indexes = [
            models.Index(fields=["status"], name="idx_wfrun_status"),
            models.Index(fields=["workflow", "created_at"], name="idx_wfrun_wf_time"),
        ]

    def __str__(self) -> str:
        return f"Run({self.workflow.name}) [{self.status}]"
