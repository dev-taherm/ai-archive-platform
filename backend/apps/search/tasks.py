from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="search.rebuild_index")
def rebuild_search_index() -> str:
    """Rebuild the search embedding index from all processed documents."""
    import asyncio

    from core.infrastructure.db.repositories.document_repository import (
        DjangoDocumentRepository,
    )
    from core.infrastructure.db.repositories.embedding_repository import (
        PgvectorEmbeddingRepository,
    )
    from core.infrastructure.services.embedding_provider import OpenAIEmbeddingProvider
    from core.application.use_cases.ai_use_cases import AIUseCases

    async def _run() -> str:
        from core.infrastructure.db.repositories.ai_repository import (
            DjangoAITaskRepository,
        )
        from core.infrastructure.db.repositories.file_repository import (
            DjangoFileRepository,
        )
        from core.infrastructure.services.llm_provider import OpenAIProvider

        doc_repo = DjangoDocumentRepository()
        emb_repo = PgvectorEmbeddingRepository()
        ai_repo = DjangoAITaskRepository()
        file_repo = DjangoFileRepository()
        llm = OpenAIProvider()
        emb = OpenAIEmbeddingProvider()

        use_cases = AIUseCases(ai_repo, doc_repo, emb_repo, file_repo, llm, emb)

        documents = await doc_repo.list_all(offset=0, limit=10000)
        total_embeddings = 0

        for doc in documents:
            if not doc.extracted_text:
                continue
            results = await use_cases.generate_embeddings(doc.id)
            total_embeddings += len(results)

        return f"Rebuilt index: {total_embeddings} embeddings from {len(documents)} documents"

    return asyncio.run(_run())


@shared_task(name="search.log_search_analytics")
def log_search_analytics(
    query: str,
    search_type: str,
    result_count: int,
    search_time_ms: float,
    user_id: str | None = None,
) -> str:
    """Log search analytics to the database."""
    from apps.search.models import SearchLog
    import uuid

    SearchLog.objects.create(
        user_id=uuid.UUID(user_id) if user_id else None,
        query=query,
        search_type=search_type,
        result_count=result_count,
        search_time_ms=search_time_ms,
    )
    return f"Logged search: {query[:50]}"
