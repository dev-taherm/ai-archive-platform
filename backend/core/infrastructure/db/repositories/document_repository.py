from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


class DjangoDocumentRepository(DocumentRepository):
    """Django ORM implementation of DocumentRepository ABC."""

    def __init__(self) -> None:
        from apps.documents.models import Document as DocumentModel

        self._model = DocumentModel

    def _qs(self) -> QuerySet:
        return self._model.objects.all()

    def _to_domain(self, obj: Any) -> Document:
        metadata = DocumentMetadata(
            title=getattr(obj, "title", ""),
            author=getattr(obj, "author", ""),
            subject=getattr(obj, "subject", ""),
            language=Language(getattr(obj, "language", "unknown")),
            word_count=getattr(obj, "word_count", 0),
            page_count=getattr(obj, "page_count", 0),
            char_count=getattr(obj, "char_count", 0),
            extra={
                "agent_version": getattr(obj, "agent_version", ""),
                "processing_version": getattr(obj, "processing_version", ""),
                "parser_version": getattr(obj, "parser_version", ""),
                "ocr_engine": getattr(obj, "ocr_engine", ""),
                "ocr_used": getattr(obj, "ocr_used", False),
                "markdown": getattr(obj, "markdown", ""),
                "content_blocks": getattr(obj, "content_blocks", []),
                "tables": getattr(obj, "tables", []),
                "images": getattr(obj, "images", []),
            },
        )
        # Try to fetch extended metadata from the related model
        try:
            if hasattr(obj, "metadata") and obj.metadata:
                meta_obj = obj.metadata
                metadata = DocumentMetadata(
                    title=getattr(meta_obj, "title", "") or metadata.title,
                    author=getattr(meta_obj, "author", "") or metadata.author,
                    subject=getattr(meta_obj, "subject", "") or metadata.subject,
                    language=Language(
                        getattr(meta_obj, "language", "unknown")
                        or metadata.language.value
                    ),
                    word_count=getattr(meta_obj, "word_count", 0)
                    or metadata.word_count,
                    char_count=getattr(meta_obj, "char_count", 0)
                    or metadata.char_count,
                    page_count=getattr(meta_obj, "page_count", 0)
                    or metadata.page_count,
                    keywords=tuple(getattr(meta_obj, "keywords", []) or []),
                    tags=tuple(getattr(meta_obj, "tags", []) or []),
                )
        except Exception:
            pass

        return Document(
            id=obj.id,
            file_id=obj.file_id,
            doc_type=DocumentType(obj.doc_type),
            processing_status=ProcessingStatus(obj.processing_status),
            metadata=metadata,
            classification_confidence=(
                Confidence(value=obj.classification_confidence)
                if obj.classification_confidence is not None
                else None
            ),
            extracted_text=obj.extracted_text,
            summary=getattr(obj, "summary", ""),
            chunk_count=obj.chunk_count,
            error_message=obj.error_message,
            retry_count=0,
            tags=tuple(obj.tags) if obj.tags else (),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        try:
            obj = self._qs().get(id=document_id)
            return self._to_domain(obj)
        except self._model.DoesNotExist:
            return None

    def get_by_file_id(self, file_id: uuid.UUID) -> Document | None:
        try:
            obj = self._qs().get(file_id=file_id)
            return self._to_domain(obj)
        except self._model.DoesNotExist:
            return None

    def save(self, document: Document) -> Document:
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
            "summary": document.summary,
            "chunk_count": document.chunk_count,
            "error_message": document.error_message or "",
            "tags": list(document.tags),
            "title": document.metadata.title,
            "author": document.metadata.author,
            "subject": document.metadata.subject,
            "language": document.metadata.language.value,
            "word_count": document.metadata.word_count,
            "char_count": document.metadata.char_count,
            "page_count": document.metadata.page_count,
        }
        extra = document.metadata.extra or {}
        if extra.get("agent_version"):
            data["agent_version"] = extra["agent_version"]
        if extra.get("processing_version"):
            data["processing_version"] = extra["processing_version"]
        if extra.get("parser_version"):
            data["parser_version"] = extra["parser_version"]
        if extra.get("ocr_engine"):
            data["ocr_engine"] = extra["ocr_engine"]
        if extra.get("ocr_used"):
            data["ocr_used"] = extra["ocr_used"]
        if extra.get("markdown"):
            data["markdown"] = extra["markdown"]
        if extra.get("content_blocks"):
            data["content_blocks"] = extra["content_blocks"]
        if extra.get("tables"):
            data["tables"] = extra["tables"]
        if extra.get("images"):
            data["images"] = extra["images"]
        obj, _ = self._model.objects.update_or_create(
            id=document.id,
            defaults=data,
        )

        # Persist extended metadata to the related model
        try:
            from apps.documents.models import DocumentMetadata as MetaModel

            MetaModel.objects.update_or_create(
                document=obj,
                defaults={
                    "keywords": list(getattr(document.metadata, "keywords", []) or []),
                    "tags": list(getattr(document.metadata, "tags", []) or []),
                    "entities": getattr(document.metadata, "entities", {}),
                    "summary": getattr(document.metadata, "summary", ""),
                    "categories": getattr(document.metadata, "categories", []),
                    "sentiment": getattr(document.metadata, "sentiment", ""),
                    "extra": getattr(document.metadata, "extra", {}),
                },
            )
        except Exception:
            logger.debug(
                "Could not save extended metadata for document %s", document.id
            )

        return self._to_domain(obj)

    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        qs = self._qs().order_by("-created_at")[offset : offset + limit]
        return [self._to_domain(obj) for obj in qs]

    def delete(self, document_id: uuid.UUID) -> bool:
        deleted_count, _ = self._qs().filter(id=document_id).delete()
        return deleted_count > 0

    def search_by_embedding(
        self,
        embedding_id: str,
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        """Search document chunks by embedding similarity using pgvector."""
        try:
            from apps.ai.models import Embedding as EmbeddingModel
            from apps.documents.models import DocumentChunk as ChunkModel

            # Find the embedding to get the document_id
            try:
                embedding_obj = EmbeddingModel.objects.get(vector_id=embedding_id)
            except EmbeddingModel.DoesNotExist:
                return []

            document_id = embedding_obj.document_id
            if not document_id:
                return []

            # Get all chunks for this document
            chunks = ChunkModel.objects.filter(document_id=document_id).order_by(
                "chunk_index"
            )

            results: list[tuple[DocumentChunk, float]] = []
            for chunk in chunks:
                doc_chunk = DocumentChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    token_estimate=chunk.token_estimate,
                )
                # Default score of 1.0 for exact document match
                results.append((doc_chunk, 1.0))

            return results[:top_k]
        except Exception:
            logger.exception("Failed to search by embedding")
            return []

    def get_chunks_by_document(
        self,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        """Retrieve all chunks belonging to a document."""
        try:
            from apps.documents.models import DocumentChunk as ChunkModel

            chunks = ChunkModel.objects.filter(document_id=document_id).order_by(
                "chunk_index"
            )

            return [
                DocumentChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    token_estimate=chunk.token_estimate,
                )
                for chunk in chunks
            ]
        except Exception:
            logger.exception("Failed to get chunks for document %s", document_id)
            return []
