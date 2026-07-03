from __future__ import annotations

import logging
import uuid

from core.application.dtos.document_dto import (
    ClassificationResultDTO,
    DocumentDTO,
    DocumentMetadataDTO,
)
from core.application.use_cases.document_use_cases import DocumentUseCases

logger = logging.getLogger(__name__)


class DocumentService:
    """Thin wrapper delegating document operations to core DocumentUseCases."""

    def __init__(self, document_use_cases: DocumentUseCases) -> None:
        self._document_use_cases = document_use_cases

    def process_document(
        self,
        file_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> DocumentDTO:
        result = self._document_use_cases.process_document(file_id)
        logger.info(
            "Document processed: file_id=%s doc_id=%s type=%s chunks=%d",
            file_id,
            result.id,
            result.doc_type,
            result.chunk_count,
        )
        return result

    def get_document(self, document_id: uuid.UUID) -> DocumentDTO:
        return self._document_use_cases.get_document(document_id)

    def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[DocumentDTO]:
        return self._document_use_cases.list_documents(offset=offset, limit=limit)

    def classify_document(
        self,
        document_id: uuid.UUID,
        *,
        categories: list[str] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ClassificationResultDTO:
        result = self._document_use_cases.classify_document(
            document_id,
            categories=categories,
        )
        logger.info(
            "Document classified: doc_id=%s type=%s confidence=%.2f",
            document_id,
            result.predicted_type,
            result.confidence,
        )
        return result

    def extract_metadata(
        self,
        document_id: uuid.UUID,
        *,
        fields: list[str] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> DocumentMetadataDTO:
        return self._document_use_cases.extract_metadata(
            document_id,
            fields=fields,
        )
