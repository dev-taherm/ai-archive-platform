from __future__ import annotations

import logging
import uuid
from typing import Any

from core.application.dtos.document_dto import (
    ClassificationResultDTO,
    DocumentDTO,
    DocumentMetadataDTO,
)
from core.application.interfaces.repositories import (
    AuditLogRepository,
)
from core.application.use_cases.document_use_cases import DocumentUseCases

logger = logging.getLogger(__name__)


class DocumentService:
    """Application service orchestrating document processing operations."""

    def __init__(
        self,
        document_use_cases: DocumentUseCases,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._document_use_cases = document_use_cases
        self._audit_log_repository = audit_log_repository

    async def process_document(
        self,
        file_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> DocumentDTO:
        """Process a document through the full pipeline and log the operation."""
        result = await self._document_use_cases.process_document(file_id)

        await self._audit(
            action="document.processed",
            user_id=user_id,
            resource_type="document",
            resource_id=result.id,
            details={
                "file_id": str(file_id),
                "doc_type": result.doc_type,
                "status": result.processing_status,
                "chunk_count": result.chunk_count,
            },
        )

        return result

    async def get_document(
        self,
        document_id: uuid.UUID,
    ) -> DocumentDTO:
        """Retrieve a document by ID."""
        return await self._document_use_cases.get_document(document_id)

    async def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[DocumentDTO]:
        """List all documents with pagination."""
        return await self._document_use_cases.list_documents(offset=offset, limit=limit)

    async def classify_document(
        self,
        document_id: uuid.UUID,
        *,
        categories: list[str] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ClassificationResultDTO:
        """Classify a document and log the operation."""
        result = await self._document_use_cases.classify_document(
            document_id,
            categories=categories,
        )

        await self._audit(
            action="document.classified",
            user_id=user_id,
            resource_type="document",
            resource_id=document_id,
            details={
                "predicted_type": result.predicted_type,
                "confidence": result.confidence,
            },
        )

        return result

    async def extract_metadata(
        self,
        document_id: uuid.UUID,
        *,
        fields: list[str] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> DocumentMetadataDTO:
        """Extract metadata from a document and log the operation."""
        result = await self._document_use_cases.extract_metadata(
            document_id,
            fields=fields,
        )

        await self._audit(
            action="document.metadata_extracted",
            user_id=user_id,
            resource_type="document",
            resource_id=document_id,
            details={"fields": fields or []},
        )

        return result

    async def _audit(
        self,
        action: str,
        user_id: uuid.UUID | None,
        resource_type: str,
        resource_id: uuid.UUID | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Persist an audit log entry."""
        try:
            await self._audit_log_repository.save({
                "action": action,
                "user_id": str(user_id) if user_id else None,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "details": details or {},
            })
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)
