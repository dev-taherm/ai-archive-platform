from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="chat.send_message_task")
def send_message_task(
    session_id: str,
    message: str,
    user_id: str | None = None,
) -> dict[str, object]:
    """Celery task to send a chat message and get an AI response."""
    import asyncio

    from apps.chat.services import ChatService
    from core.application.use_cases.chat_use_cases import ChatUseCases

    async def _run() -> dict[str, object]:
        from core.infrastructure.db.repositories.document_repository import (
            DjangoDocumentRepository,
        )
        from core.infrastructure.db.repositories.embedding_repository import (
            PgvectorEmbeddingRepository,
        )
        from core.infrastructure.services.embedding_provider import OpenAIEmbeddingProvider
        from core.infrastructure.services.llm_provider import OpenAIProvider

        doc_repo = DjangoDocumentRepository()
        emb_repo = PgvectorEmbeddingRepository()
        llm = OpenAIProvider()
        emb = OpenAIEmbeddingProvider()
        use_cases = ChatUseCases(doc_repo, emb_repo, llm, emb)
        service = ChatService(use_cases)

        response = await service.send_message(
            uuid.UUID(session_id),
            message,
            user_id=uuid.UUID(user_id) if user_id else None,
        )

        return {
            "response": response.message.content[:200],
            "processing_time_ms": response.processing_time_ms,
            "session_id": str(response.session_id),
        }

    return asyncio.run(_run())
