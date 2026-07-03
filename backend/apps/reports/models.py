from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Report(models.Model):
    """Generated analytics and summary reports."""

    class ReportType(models.TextChoices):
        ARCHIVE_SUMMARY = "archive_summary", "Archive Summary"
        PROCESSING_STATS = "processing_stats", "Processing Stats"
        SEARCH_ANALYTICS = "search_analytics", "Search Analytics"
        USER_ACTIVITY = "user_activity", "User Activity"
        STORAGE_USAGE = "storage_usage", "Storage Usage"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATING = "generating", "Generating"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    parameters = models.JSONField(default=dict, blank=True)
    data = models.JSONField(default=dict, blank=True)
    file_path = models.CharField(max_length=500, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports_report"
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        indexes = [
            models.Index(fields=["report_type", "status"], name="idx_report_type_status"),
            models.Index(fields=["created_at"], name="idx_report_created"),
        ]

    def __str__(self) -> str:
        return f"{self.title} [{self.report_type}]"
