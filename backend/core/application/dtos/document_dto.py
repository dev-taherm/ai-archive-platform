from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DocumentDTO:
    """Data transfer object for document information."""

    id: uuid.UUID
    file_id: uuid.UUID
    doc_type: str
    processing_status: str
    title: str = ""
    author: str = ""
    subject: str = ""
    language: str = "unknown"
    word_count: int = 0
    page_count: int = 0
    chunk_count: int = 0
    classification_confidence: float | None = None
    tags: tuple[str, ...] = ()
    extracted_text_preview: str = ""
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_entity(cls, document: Any) -> DocumentDTO:
        """Create a DTO from a Document domain entity."""
        text_preview = (
            document.extracted_text[:200] + "..."
            if len(document.extracted_text) > 200
            else document.extracted_text
        )
        return cls(
            id=document.id,
            file_id=document.file_id,
            doc_type=document.doc_type.value,
            processing_status=document.processing_status.value,
            title=document.metadata.title,
            author=document.metadata.author,
            subject=document.metadata.subject,
            language=document.metadata.language.value,
            word_count=document.word_count,
            page_count=document.metadata.page_count,
            chunk_count=document.chunk_count,
            classification_confidence=(
                document.classification_confidence.value
                if document.classification_confidence
                else None
            ),
            tags=tuple(document.tags),
            extracted_text_preview=text_preview,
            error_message=document.error_message,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


@dataclass(frozen=True)
class DocumentMetadataDTO:
    """Data transfer object for document metadata."""

    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: tuple[str, ...] = ()
    creation_date: str = ""
    modification_date: str = ""
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    language: str = "unknown"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_entity(cls, metadata: Any) -> DocumentMetadataDTO:
        """Create a DTO from a DocumentMetadata value object."""
        return cls(
            title=metadata.title,
            author=metadata.author,
            subject=metadata.subject,
            keywords=metadata.keywords,
            creation_date=metadata.creation_date,
            modification_date=metadata.modification_date,
            page_count=metadata.page_count,
            word_count=metadata.word_count,
            char_count=metadata.char_count,
            language=metadata.language.value,
            extra=metadata.extra,
        )


@dataclass(frozen=True)
class ClassificationResultDTO:
    """Data transfer object for document classification results."""

    document_id: uuid.UUID
    predicted_type: str
    confidence: float
    all_scores: dict[str, float] = field(default_factory=dict)
    model_used: str = ""
    classified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
