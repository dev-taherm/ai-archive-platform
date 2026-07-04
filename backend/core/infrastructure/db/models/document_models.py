from __future__ import annotations


from django.contrib.postgres.fields import ArrayField
from django.db import models

from core.domain.documents.entities import Document, DocumentChunk, DocumentMetadata
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)
from core.infrastructure.db.models.base import BaseModel


class DocumentModel(BaseModel):
    """Django ORM model for Document domain entity."""

    file_id = models.UUIDField(db_index=True)
    doc_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.value) for t in DocumentType],
        default=DocumentType.UNKNOWN.value,
        db_index=True,
    )
    processing_status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in ProcessingStatus],
        default=ProcessingStatus.QUEUED.value,
        db_index=True,
    )
    classification_confidence = models.FloatField(null=True, blank=True)
    extracted_text = models.TextField(blank=True, default="")
    chunk_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    tags = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
    )

    class Meta:
        db_table = "document"
        indexes = [
            models.Index(fields=["file_id"], name="idx_doc_file"),
            models.Index(fields=["processing_status"], name="idx_doc_status"),
            models.Index(fields=["doc_type"], name="idx_doc_type"),
        ]

    def __str__(self) -> str:
        return f"Document({self.id}, type={self.doc_type})"

    def to_domain(self) -> Document:
        return Document(
            id=self.id,
            file_id=self.file_id,
            doc_type=DocumentType(self.doc_type),
            processing_status=ProcessingStatus(self.processing_status),
            metadata=self._build_metadata(),
            classification_confidence=(
                Confidence(value=self.classification_confidence)
                if self.classification_confidence is not None
                else None
            ),
            extracted_text=self.extracted_text,
            chunk_count=self.chunk_count,
            error_message=self.error_message,
            retry_count=self.retry_count,
            tags=list(self.tags) if self.tags else [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def _build_metadata(self) -> DocumentMetadata:
        return DocumentMetadata()

    @classmethod
    def from_domain(cls, entity: Document) -> DocumentModel:
        return cls(
            id=entity.id,
            file_id=entity.file_id,
            doc_type=entity.doc_type.value,
            processing_status=entity.processing_status.value,
            classification_confidence=(
                entity.classification_confidence.value
                if entity.classification_confidence is not None
                else None
            ),
            extracted_text=entity.extracted_text,
            chunk_count=entity.chunk_count,
            error_message=entity.error_message,
            retry_count=entity.retry_count,
            tags=entity.tags,
        )


class DocumentMetadataModel(BaseModel):
    """Django ORM model for DocumentMetadata value object.

    Stored as a separate table to allow flexible metadata queries without
    bloating the core Document row.
    """

    document = models.OneToOneField(
        DocumentModel,
        on_delete=models.CASCADE,
        related_name="metadata_record",
    )
    title = models.CharField(max_length=500, blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")
    subject = models.CharField(max_length=500, blank=True, default="")
    keywords = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
    )
    creation_date = models.CharField(max_length=30, blank=True, default="")
    modification_date = models.CharField(max_length=30, blank=True, default="")
    page_count = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    char_count = models.PositiveIntegerField(default=0)
    language = models.CharField(
        max_length=10,
        choices=[(l.value, l.value) for l in Language],
        default=Language.UNKNOWN.value,
    )
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "document_metadata"

    def __str__(self) -> str:
        return f"DocumentMetadata(doc={self.document_id}, title={self.title[:40]})"

    def to_domain(self) -> DocumentMetadata:
        return DocumentMetadata(
            title=self.title,
            author=self.author,
            subject=self.subject,
            keywords=tuple(self.keywords) if self.keywords else (),
            creation_date=self.creation_date,
            modification_date=self.modification_date,
            page_count=self.page_count,
            word_count=self.word_count,
            char_count=self.char_count,
            language=Language(self.language),
            extra=dict(self.extra) if self.extra else {},
        )

    @classmethod
    def from_domain(cls, entity: DocumentMetadata, document_id: str) -> DocumentMetadataModel:
        return cls(
            document_id=document_id,
            title=entity.title,
            author=entity.author,
            subject=entity.subject,
            keywords=list(entity.keywords),
            creation_date=entity.creation_date,
            modification_date=entity.modification_date,
            page_count=entity.page_count,
            word_count=entity.word_count,
            char_count=entity.char_count,
            language=entity.language.value,
            extra=entity.extra,
        )


class DocumentChunkModel(BaseModel):
    """Django ORM model for DocumentChunk domain entity."""

    document = models.ForeignKey(
        DocumentModel,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    start_offset = models.IntegerField(default=0)
    end_offset = models.IntegerField(default=0)
    embedding_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "document_chunk"
        indexes = [
            models.Index(fields=["document", "chunk_index"], name="idx_chunk_doc_idx"),
            models.Index(fields=["embedding_id"], name="idx_chunk_embedding"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="uq_chunk_doc_index",
            ),
        ]

    def __str__(self) -> str:
        return f"DocumentChunk(doc={self.document_id}, idx={self.chunk_index})"

    def to_domain(self) -> DocumentChunk:
        return DocumentChunk(
            id=self.id,
            document_id=self.document_id,
            chunk_index=self.chunk_index,
            content=self.content,
            start_offset=self.start_offset,
            end_offset=self.end_offset,
            embedding_id=self.embedding_id,
            metadata=dict(self.metadata) if self.metadata else {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: DocumentChunk, document_id: str | None = None) -> DocumentChunkModel:
        return cls(
            id=entity.id,
            document_id=document_id or str(entity.document_id),
            chunk_index=entity.chunk_index,
            content=entity.content,
            start_offset=entity.start_offset,
            end_offset=entity.end_offset,
            embedding_id=entity.embedding_id,
            metadata=entity.metadata,
        )
