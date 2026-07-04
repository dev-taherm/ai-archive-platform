from __future__ import annotations

import uuid
from typing import Sequence

from apps.documents.models import Document as DjangoDocument
from core.application.interfaces.repositories import DocumentRepository
from core.domain.documents.entities import Document, DocumentChunk, DocumentMetadata
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)


class DjangoDocumentRepository(DocumentRepository):
    """Django ORM implementation of the DocumentRepository interface."""

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        try:
            orm = DjangoDocument.objects.get(pk=document_id)
            return self._to_entity(orm)
        except DjangoDocument.DoesNotExist:
            return None

    def save(self, document: Document) -> Document:
        orm = self._to_orm(document)
        orm.save()
        return self._to_entity(orm)

    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        qs = DjangoDocument.objects.all().order_by("-created_at")[offset : offset + limit]
        return [self._to_entity(orm) for orm in qs]

    def delete(self, document_id: uuid.UUID) -> bool:
        deleted, _ = DjangoDocument.objects.filter(pk=document_id).delete()
        return deleted > 0

    def search_by_embedding(
        self,
        embedding_id: str,
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        # Requires a vector database (pgvector, pinecone, etc.)
        # This is a placeholder for when vector search is integrated
        return []

    def get_chunks_by_document(
        self,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        try:
            orm = DjangoDocument.objects.get(pk=document_id)
        except DjangoDocument.DoesNotExist:
            return []

        if not orm.extracted_text:
            return []

        chunk_size = 1000
        overlap = 200
        chunks: list[DocumentChunk] = []
        text = orm.extracted_text
        start = 0
        index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    chunk_index=index,
                    content=text[start:end],
                    start_offset=start,
                    end_offset=end,
                )
            )
            index += 1
            if end >= len(text):
                break
            start = end - overlap

        return chunks

    @staticmethod
    def _to_entity(orm: DjangoDocument) -> Document:
        doc_type_map = {
            "invoice": DocumentType.UNKNOWN,
            "contract": DocumentType.UNKNOWN,
            "report": DocumentType.UNKNOWN,
            "letter": DocumentType.UNKNOWN,
            "memo": DocumentType.UNKNOWN,
            "receipt": DocumentType.UNKNOWN,
            "unknown": DocumentType.UNKNOWN,
        }

        status_map = {
            "pending": ProcessingStatus.QUEUED,
            "processing": ProcessingStatus.EXTRACTING,
            "indexing": ProcessingStatus.INDEXING,
            "completed": ProcessingStatus.COMPLETED,
            "failed": ProcessingStatus.FAILED,
        }

        return Document(
            id=orm.id,
            file_id=orm.file_id,
            doc_type=doc_type_map.get(orm.doc_type, DocumentType.UNKNOWN),
            processing_status=status_map.get(orm.processing_status, ProcessingStatus.QUEUED),
            metadata=DocumentMetadata(
                title=orm.title,
                author=orm.author,
                subject=orm.subject,
                language=Language(orm.language) if orm.language != "unknown" else Language.UNKNOWN,
                word_count=orm.word_count,
                page_count=orm.page_count,
            ),
            classification_confidence=(
                Confidence(value=orm.classification_confidence)
                if orm.classification_confidence is not None
                else None
            ),
            extracted_text=orm.extracted_text,
            chunk_count=orm.chunk_count,
            error_message=orm.error_message or None,
            tags=tuple(orm.tags),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _to_orm(entity: Document) -> DjangoDocument:
        doc_type_map = {
            DocumentType.PDF: "unknown",
            DocumentType.TEXT: "unknown",
            DocumentType.MARKDOWN: "unknown",
            DocumentType.HTML: "unknown",
            DocumentType.CSV: "unknown",
            DocumentType.JSON: "unknown",
            DocumentType.CODE: "unknown",
            DocumentType.EMAIL: "unknown",
            DocumentType.SPREADSHEET: "unknown",
            DocumentType.PRESENTATION: "unknown",
            DocumentType.UNKNOWN: "unknown",
        }

        status_map = {
            ProcessingStatus.QUEUED: "pending",
            ProcessingStatus.EXTRACTING: "processing",
            ProcessingStatus.CLASSIFYING: "processing",
            ProcessingStatus.INDEXING: "indexing",
            ProcessingStatus.COMPLETED: "completed",
            ProcessingStatus.FAILED: "failed",
            ProcessingStatus.RETRYING: "processing",
        }

        return DjangoDocument(
            id=entity.id,
            file_id=entity.file_id,
            doc_type=doc_type_map.get(entity.doc_type, "unknown"),
            processing_status=status_map.get(entity.processing_status, "pending"),
            title=entity.metadata.title,
            author=entity.metadata.author,
            subject=entity.metadata.subject,
            language=entity.metadata.language.value,
            word_count=entity.metadata.word_count,
            page_count=entity.metadata.page_count,
            chunk_count=entity.chunk_count,
            classification_confidence=(
                entity.classification_confidence.value
                if entity.classification_confidence
                else None
            ),
            tags=list(entity.tags),
            extracted_text=entity.extracted_text,
            error_message=entity.error_message or "",
        )
