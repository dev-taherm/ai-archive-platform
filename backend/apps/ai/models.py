from __future__ import annotations

import uuid

from django.db import models


class AITask(models.Model):
    """Tracks AI processing tasks for audit and monitoring."""

    class TaskType(models.TextChoices):
        CLASSIFY = "classify", "Classify"
        EXTRACT = "extract", "Extract"
        SUMMARIZE = "summarize", "Summarize"
        EMBED = "embed", "Embed"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    document_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    input_preview = models.TextField(blank=True, default="")
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    processing_time_ms = models.FloatField(null=True, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    model_used = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_aitask"
        verbose_name = "AI Task"
        verbose_name_plural = "AI Tasks"
        indexes = [
            models.Index(fields=["task_type", "status"], name="idx_aitask_type_status"),
            models.Index(fields=["document_id"], name="idx_aitask_document"),
            models.Index(fields=["created_at"], name="idx_aitask_created"),
        ]

    def __str__(self) -> str:
        return f"AITask({self.task_type}) [{self.status}]"
