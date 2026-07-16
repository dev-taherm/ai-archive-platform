from __future__ import annotations

import uuid

from django.conf import settings
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
        IMAGE = "image", "Image"
        UNKNOWN = "unknown", "Unknown"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        INDEXING = "indexing", "Indexing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_documents",
    )
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
    summary = models.TextField(blank=True, default="")
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


class ExtractedEntity(models.Model):
    """A named entity extracted from a document by the LLM pipeline."""

    class EntityType(models.TextChoices):
        PERSON = "person", "Person"
        ORGANIZATION = "organization", "Organization"
        DATE = "date", "Date"
        AMOUNT = "amount", "Amount"
        LOCATION = "location", "Location"
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        REFERENCE_NUMBER = "reference_number", "Reference Number"
        PROJECT_NAME = "project_name", "Project Name"

    class Source(models.TextChoices):
        PIPELINE = "pipeline", "Pipeline"
        AGENT = "agent", "Agent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="entities",
    )
    entity_type = models.CharField(
        max_length=30,
        choices=EntityType.choices,
    )
    name = models.CharField(max_length=500)
    context = models.TextField(blank=True, default="")
    confidence = models.FloatField(null=True, blank=True)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.PIPELINE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_extractedentity"
        verbose_name = "Extracted Entity"
        verbose_name_plural = "Extracted Entities"
        indexes = [
            models.Index(fields=["entity_type"], name="idx_entity_type"),
            models.Index(fields=["name"], name="idx_entity_name"),
            models.Index(fields=["document", "entity_type"], name="idx_entity_doc_type"),
        ]

    def __str__(self) -> str:
        return f"{self.entity_type}: {self.name}"
