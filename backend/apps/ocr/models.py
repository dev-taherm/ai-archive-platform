from __future__ import annotations

import uuid

from django.db import models


class OCRJob(models.Model):
    """Tracks OCR processing jobs for audit and retry purposes."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_id = models.UUIDField(db_index=True)
    document_id = models.UUIDField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    source_type = models.CharField(
        max_length=20,
        choices=[("image", "Image"), ("pdf", "PDF")],
    )
    extracted_text = models.TextField(blank=True, default="")
    confidence = models.FloatField(null=True, blank=True)
    language = models.CharField(max_length=10, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    processing_time_ms = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ocr_ocrjob"
        verbose_name = "OCR Job"
        verbose_name_plural = "OCR Jobs"
        indexes = [
            models.Index(fields=["status"], name="idx_ocrjob_status"),
            models.Index(fields=["source_type"], name="idx_ocrjob_source"),
        ]

    def __str__(self) -> str:
        return f"OCRJob({self.id}) [{self.status}]"
