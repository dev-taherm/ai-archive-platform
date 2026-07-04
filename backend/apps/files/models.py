from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class FileRecord(models.Model):
    """Django ORM model mirroring the FileRecord domain entity for admin/queries."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INDEXING = "indexing", "Indexing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    path = models.TextField()
    mime_type = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    content_hash = models.CharField(max_length=128, blank=True, default="")
    checksum = models.CharField(max_length=128, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    duplicate_group_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_filerecord"
        verbose_name = "File Record"
        verbose_name_plural = "File Records"
        indexes = [
            models.Index(fields=["status"], name="idx_filerecord_status"),
            models.Index(fields=["mime_type"], name="idx_filerecord_mime"),
            models.Index(fields=["content_hash"], name="idx_filerecord_hash"),
        ]

    def __str__(self) -> str:
        return self.path


class AuditLog(models.Model):
    """Tracks all user and system actions for compliance and debugging."""

    class ActionType(models.TextChoices):
        CREATE = "create", "Create"
        READ = "read", "Read"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        UPLOAD = "upload", "Upload"
        DOWNLOAD = "download", "Download"
        SCAN = "scan", "Scan"
        PROCESS = "process", "Process"
        CLASSIFY = "classify", "Classify"
        SEARCH = "search", "Search"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    resource_type = models.CharField(max_length=100, blank=True, default="")
    resource_id = models.CharField(max_length=100, blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "files_auditlog"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="idx_auditlog_user_time"),
            models.Index(fields=["action"], name="idx_auditlog_action"),
            models.Index(fields=["resource_type", "resource_id"], name="idx_auditlog_resource"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.resource_type}/{self.resource_id}"
