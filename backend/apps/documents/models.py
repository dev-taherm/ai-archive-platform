from __future__ import annotations

import uuid

from django.db import models


class Document(models.Model):
    """Django ORM model mirroring the Document domain entity for admin/queries."""

    class DocType(models.TextChoices):
        INVOICE = "invoice", "Invoice"
        CONTRACT = "contract", "Contract"
        REPORT = "report", "Report"
        LETTER = "letter", "Letter"
        MEMO = "memo", "Memo"
        RECEIPT = "receipt", "Receipt"
        UNKNOWN = "unknown", "Unknown"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        INDEXING = "indexing", "Indexing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_id = models.UUIDField(db_index=True)
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        default=DocType.UNKNOWN,
    )
    processing_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    title = models.CharField(max_length=500, blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")
    subject = models.CharField(max_length=500, blank=True, default="")
    language = models.CharField(max_length=10, default="unknown")
    word_count = models.PositiveIntegerField(default=0)
    page_count = models.PositiveIntegerField(default=0)
    chunk_count = models.PositiveIntegerField(default=0)
    classification_confidence = models.FloatField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    extracted_text = models.TextField(blank=True, default="")
    char_count = models.PositiveIntegerField(default=0)
    agent_version = models.CharField(max_length=20, blank=True, default="")
    processing_version = models.CharField(max_length=50, blank=True, default="")
    parser_version = models.CharField(max_length=50, blank=True, default="")
    ocr_engine = models.CharField(max_length=50, blank=True, default="")
    ocr_used = models.BooleanField(default=False)
    markdown = models.TextField(blank=True, default="")
    content_blocks = models.JSONField(default=list, blank=True)
    tables = models.JSONField(default=list, blank=True)
    images = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents_document"
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        indexes = [
            models.Index(fields=["doc_type"], name="idx_document_type"),
            models.Index(fields=["processing_status"], name="idx_document_status"),
            models.Index(fields=["file_id"], name="idx_document_file"),
        ]

    def __str__(self) -> str:
        return self.title or f"Document({self.id})"
