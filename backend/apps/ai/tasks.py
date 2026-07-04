from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


def _build_ai_service():
    """Build AIService with all dependencies."""
    from apps.ai.services import AIService
    from core.application.use_cases.ai_use_cases import AIUseCases
    from core.infrastructure.db.repositories.ai_repository import (
        DjangoAITaskRepository,
    )
    from core.infrastructure.db.repositories.document_repository import (
        DjangoDocumentRepository,
    )
    from core.infrastructure.db.repositories.embedding_repository import (
        PgvectorEmbeddingRepository,
    )
    from core.infrastructure.db.repositories.file_repository import (
        DjangoFileRepository,
    )
    from core.infrastructure.services.stub_providers import (
        StubEmbeddingProvider,
        StubLLMProvider,
    )

    ai_repo = DjangoAITaskRepository()
    doc_repo = DjangoDocumentRepository()
    emb_repo = PgvectorEmbeddingRepository()
    file_repo = DjangoFileRepository()
    llm = StubLLMProvider()
    emb = StubEmbeddingProvider()
    use_cases = AIUseCases(ai_repo, doc_repo, emb_repo, file_repo, llm, emb)
    return AIService(use_cases)


@shared_task(name="ai.classify_task")
def classify_task(
    text: str,
    categories: list[str] | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    """Celery task to classify text content."""
    service = _build_ai_service()
    result = service.classify(
        text,
        categories=categories,
        user_id=uuid.UUID(user_id) if user_id else None,
    )
    return {
        "predicted_label": result.predicted_label,
        "confidence": result.confidence,
    }


@shared_task(name="ai.summarize_task")
def summarize_task(
    text: str,
    max_tokens: int = 500,
    user_id: str | None = None,
) -> dict[str, object]:
    """Celery task to summarize text content."""
    service = _build_ai_service()
    result = service.summarize(
        text,
        max_tokens=max_tokens,
        user_id=uuid.UUID(user_id) if user_id else None,
    )
    return {"summary": result, "length": len(result)}


@shared_task(name="ai.generate_embeddings_task")
def generate_embeddings_task(
    document_id: str,
    user_id: str | None = None,
) -> dict[str, object]:
    """Celery task to generate embeddings for a document."""
    service = _build_ai_service()
    results = service.generate_embeddings(
        uuid.UUID(document_id),
        user_id=uuid.UUID(user_id) if user_id else None,
    )
    return {"embedding_count": len(results), "document_id": document_id}
