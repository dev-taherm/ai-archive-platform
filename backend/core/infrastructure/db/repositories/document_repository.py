from __future__ import annotations

import uuid
from typing import Any, Sequence

from django.db.models import QuerySet

from core.application.interfaces.repositories import DocumentRepository
from core.domain.documents.entities import Document, DocumentChunk, DocumentMetadata
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)


class DjangoDocumentRepository(DocumentRepository):
    """Django ORM implementation of DocumentRepository ABC.

    Uses apps.documents.models.Document as the canonical ORM model.
    """

    def __init__(self) -> None:
        from apps.documents.models import Document as DocumentModel
        self._model = DocumentModel

    def _qs(self) -> QuerySet:
        return self._model.objects.all()

    def _to_domain(self, obj: Any) -> Document:
        return Document(
            id=obj.id,
            file_id=obj.file_id,
            doc_type=DocumentType(obj.doc_type),
            processing_status=ProcessingStatus(obj.processing_status),
            metadata=DocumentMetadata(
                title=getattr(obj, "title", ""),
                author=getattr(obj, "author", ""),
                subject=getattr(obj, "subject", ""),
                language=Language(getattr(obj, "language", "unknown")),
                word_count=getattr(obj, "word_count", 0),
                page_count=getattr(obj, "page_count", 0),
            ),
            classification_confidence=(
                Confidence(value=obj.classification_confidence)
                if obj.classification_confidence is not None
                else None
            ),
            extracted_text=obj.extracted_text,
            chunk_count=obj.chunk_count,
            error_message=obj.error_message,
            retry_count=0,
            tags=list(obj.tags) if obj.tags else [],
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        try:
            obj = await self._qs().aget(id=document_id)
            return self._to_domain(obj)
        except self._model.DoesNotExist:
            return None

    async def save(self, document: Document) -> Document:
        data = {
            "id": document.id,
            "file_id": document.file_id,
            "doc_type": document.doc_type.value,
            "processing_status": document.processing_status.value,
            "classification_confidence": (
                document.classification_confidence.value
                if document.classification_confidence is not None
                else None
            ),
            "extracted_text": document.extracted_text,
            "chunk_count": document.chunk_count,
            "error_message": document.error_message,
            "tags": document.tags,
            "title": document.metadata.title,
            "author": document.metadata.author,
            "subject": document.metadata.subject,
            "language": document.metadata.language.value,
            "word_count": document.metadata.word_count,
            "page_count": document.metadata.page_count,
        }
        obj, _ = await self._model.objects.aupdate_or_create(
            id=document.id,
            defaults=data,
        )
        return self._to_domain(obj)

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        qs = self._qs().order_by("-created_at")[offset : offset + limit]
        return [self._to_domain(obj) async for obj in qs]

    async def delete(self, document_id: uuid.UUID) -> bool:
        deleted_count, _ = await self._qs().filter(id=document_id).adelete()
        return deleted_count > 0

    async def search_by_embedding(
        self,
        embedding_id: str,
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        qs = self._qs().filter(embedding_id__isnull=False)[:top_k]
        results: list[tuple[DocumentChunk, float]] = []
        async for obj in qs:
            chunk = DocumentChunk(
                id=uuid.uuid4(),
                document_id=obj.id,
                chunk_index=0,
                content=obj.extracted_text[:1000] if obj.extracted_text else "",
            )
            results.append((chunk, 1.0))
        return results

    async def get_chunks_by_document(
        self,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        return []
