from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="documents.process_document_task")
def process_document_task(file_id: str) -> dict[str, object]:
    """Celery task to process a document through the full pipeline."""
    import asyncio

    from apps.documents.services import DocumentService
    from core.application.use_cases.document_use_cases import DocumentUseCases

    async def _run() -> dict[str, object]:
        from core.infrastructure.db.repositories.document_repository import (
            DjangoDocumentRepository,
        )
        from core.infrastructure.db.repositories.embedding_repository import (
            PgvectorEmbeddingRepository,
        )
        from core.infrastructure.db.repositories.file_repository import (
            DjangoFileRepository,
        )
        from core.infrastructure.services.llm_provider import OpenAIProvider
        from core.infrastructure.services.ocr_provider import TesseractOCRProvider

        doc_repo = DjangoDocumentRepository()
        file_repo = DjangoFileRepository()
        emb_repo = PgvectorEmbeddingRepository()
        ocr = TesseractOCRProvider()
        llm = OpenAIProvider()
        use_cases = DocumentUseCases(doc_repo, file_repo, emb_repo, ocr, llm)
        service = DocumentService(use_cases)

        result = await service.process_document(uuid.UUID(file_id))
        return {
            "document_id": str(result.id),
            "doc_type": result.doc_type,
            "status": result.processing_status,
            "chunk_count": result.chunk_count,
        }

    return asyncio.run(_run())


@shared_task(name="documents.classify_document_task")
def classify_document_task(
    document_id: str,
    categories: list[str] | None = None,
) -> dict[str, object]:
    """Celery task to classify a document."""
    import asyncio

    from apps.documents.services import DocumentService
    from core.application.use_cases.document_use_cases import DocumentUseCases

    async def _run() -> dict[str, object]:
        from core.infrastructure.db.repositories.document_repository import (
            DjangoDocumentRepository,
        )
        from core.infrastructure.db.repositories.embedding_repository import (
            PgvectorEmbeddingRepository,
        )
        from core.infrastructure.db.repositories.file_repository import (
            DjangoFileRepository,
        )
        from core.infrastructure.services.llm_provider import OpenAIProvider
        from core.infrastructure.services.ocr_provider import TesseractOCRProvider

        doc_repo = DjangoDocumentRepository()
        file_repo = DjangoFileRepository()
        emb_repo = PgvectorEmbeddingRepository()
        ocr = TesseractOCRProvider()
        llm = OpenAIProvider()
        use_cases = DocumentUseCases(doc_repo, file_repo, emb_repo, ocr, llm)
        service = DocumentService(use_cases)

        result = await service.classify_document(
            uuid.UUID(document_id),
            categories=categories,
        )
        return {
            "document_id": str(result.document_id),
            "predicted_type": result.predicted_type,
            "confidence": result.confidence,
        }

    return asyncio.run(_run())
