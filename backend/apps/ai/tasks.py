from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="ai.classify_task")
def classify_task(
    text: str,
    categories: list[str] | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    """Celery task to classify text content."""
    import asyncio

    from apps.ai.services import AIService
    from core.application.use_cases.ai_use_cases import AIUseCases

    async def _run() -> dict[str, object]:
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
        from core.infrastructure.services.embedding_provider import OpenAIEmbeddingProvider
        from core.infrastructure.services.llm_provider import OpenAIProvider

        ai_repo = DjangoAITaskRepository()
        doc_repo = DjangoDocumentRepository()
        emb_repo = PgvectorEmbeddingRepository()
        file_repo = DjangoFileRepository()
        llm = OpenAIProvider()
        emb = OpenAIEmbeddingProvider()
        use_cases = AIUseCases(ai_repo, doc_repo, emb_repo, file_repo, llm, emb)
        service = AIService(use_cases)

        result = await service.classify(
            text,
            categories=categories,
            user_id=uuid.UUID(user_id) if user_id else None,
        )
        return {
            "predicted_label": result.predicted_label,
            "confidence": result.confidence,
        }

    return asyncio.run(_run())


@shared_task(name="ai.summarize_task")
def summarize_task(
    text: str,
    max_tokens: int = 500,
    user_id: str | None = None,
) -> dict[str, object]:
    """Celery task to summarize text content."""
    import asyncio

    from apps.ai.services import AIService
    from core.application.use_cases.ai_use_cases import AIUseCases

    async def _run() -> dict[str, object]:
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
        from core.infrastructure.services.embedding_provider import OpenAIEmbeddingProvider
        from core.infrastructure.services.llm_provider import OpenAIProvider

        ai_repo = DjangoAITaskRepository()
        doc_repo = DjangoDocumentRepository()
        emb_repo = PgvectorEmbeddingRepository()
        file_repo = DjangoFileRepository()
        llm = OpenAIProvider()
        emb = OpenAIEmbeddingProvider()
        use_cases = AIUseCases(ai_repo, doc_repo, emb_repo, file_repo, llm, emb)
        service = AIService(use_cases)

        result = await service.summarize(
            text,
            max_tokens=max_tokens,
            user_id=uuid.UUID(user_id) if user_id else None,
        )
        return {"summary": result, "length": len(result)}

    return asyncio.run(_run())


@shared_task(name="ai.generate_embeddings_task")
def generate_embeddings_task(
    document_id: str,
    user_id: str | None = None,
) -> dict[str, object]:
    """Celery task to generate embeddings for a document."""
    import asyncio

    from apps.ai.services import AIService
    from core.application.use_cases.ai_use_cases import AIUseCases

    async def _run() -> dict[str, object]:
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
        from core.infrastructure.services.embedding_provider import OpenAIEmbeddingProvider
        from core.infrastructure.services.llm_provider import OpenAIProvider

        ai_repo = DjangoAITaskRepository()
        doc_repo = DjangoDocumentRepository()
        emb_repo = PgvectorEmbeddingRepository()
        file_repo = DjangoFileRepository()
        llm = OpenAIProvider()
        emb = OpenAIEmbeddingProvider()
        use_cases = AIUseCases(ai_repo, doc_repo, emb_repo, file_repo, llm, emb)
        service = AIService(use_cases)

        results = await service.generate_embeddings(
            uuid.UUID(document_id),
            user_id=uuid.UUID(user_id) if user_id else None,
        )
        return {"embedding_count": len(results), "document_id": document_id}

    return asyncio.run(_run())
