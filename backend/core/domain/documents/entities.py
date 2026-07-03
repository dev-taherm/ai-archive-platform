from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.domain.common.entities import BaseEntity
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)


@dataclass(frozen=True)
class DocumentMetadata:
    """Immutable metadata extracted from or associated with a document."""

    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: tuple[str, ...] = ()
    creation_date: str = ""
    modification_date: str = ""
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    language: Language = Language.UNKNOWN
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk(BaseEntity):
    """A chunk of a document for indexing and retrieval."""

    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    chunk_index: int = 0
    content: str = ""
    start_offset: int = 0
    end_offset: int = 0
    embedding_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def token_estimate(self) -> int:
        """Rough estimate of token count (4 chars per token)."""
        return len(self.content) // 4

    @classmethod
    def from_text(
        cls,
        document_id: uuid.UUID,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[DocumentChunk]:
        """Split text into overlapping chunks."""
        chunks: list[DocumentChunk] = []
        if not text:
            return chunks

        start = 0
        index = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append(
                cls(
                    document_id=document_id,
                    chunk_index=index,
                    content=chunk_text,
                    start_offset=start,
                    end_offset=end,
                )
            )
            index += 1
            if end >= len(text):
                break
            start = end - overlap
        return chunks


@dataclass(frozen=True)
class Document(BaseEntity):
    """Core document entity representing an indexed document."""

    file_id: uuid.UUID = field(default_factory=uuid.uuid4)
    doc_type: DocumentType = DocumentType.UNKNOWN
    processing_status: ProcessingStatus = ProcessingStatus.QUEUED
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    classification_confidence: Confidence | None = None
    extracted_text: str = ""
    chunk_count: int = 0
    error_message: str | None = None
    retry_count: int = 0
    tags: tuple[str, ...] = ()

    def start_processing(self) -> None:
        object.__setattr__(self, "processing_status", ProcessingStatus.EXTRACTING)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def mark_classified(self, doc_type: DocumentType, confidence: Confidence) -> None:
        object.__setattr__(self, "doc_type", doc_type)
        object.__setattr__(self, "classification_confidence", confidence)
        object.__setattr__(self, "processing_status", ProcessingStatus.INDEXING)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def mark_indexed(self, chunk_count: int) -> None:
        object.__setattr__(self, "processing_status", ProcessingStatus.COMPLETED)
        object.__setattr__(self, "chunk_count", chunk_count)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def mark_failed(self, error: str) -> None:
        object.__setattr__(self, "processing_status", ProcessingStatus.FAILED)
        object.__setattr__(self, "error_message", error)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def schedule_retry(self) -> None:
        object.__setattr__(self, "retry_count", self.retry_count + 1)
        object.__setattr__(self, "processing_status", ProcessingStatus.RETRYING)
        object.__setattr__(self, "error_message", None)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    @property
    def is_processed(self) -> bool:
        return self.processing_status == ProcessingStatus.COMPLETED

    @property
    def has_failed(self) -> bool:
        return self.processing_status == ProcessingStatus.FAILED

    @property
    def can_retry(self) -> bool:
        return self.processing_status.can_retry and self.retry_count < 3

    @property
    def word_count(self) -> int:
        return len(self.extracted_text.split()) if self.extracted_text else 0
