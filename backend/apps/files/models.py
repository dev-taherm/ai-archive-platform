from __future__ import annotations

import uuid

from django.contrib import admin
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
