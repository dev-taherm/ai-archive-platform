from __future__ import annotations

import logging
import uuid
from typing import Any

from core.application.dtos.ai_dto import AIResultDTO, ClassificationDTO, EmbeddingDTO
from core.application.use_cases.ai_use_cases import AIUseCases

logger = logging.getLogger(__name__)


class AIService:
    """Thin wrapper delegating AI operations to core AIUseCases."""

    def __init__(self, ai_use_cases: AIUseCases) -> None:
        self._ai_use_cases = ai_use_cases

    def classify(
        self,
        text: str,
        *,
        categories: list[str] | None = None,
        system_prompt: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ClassificationDTO:
        """Classify text content using the LLM provider."""
        import asyncio
        result = asyncio.run(self._ai_use_cases.classify(
            text,
            categories=categories,
            system_prompt=system_prompt,
        ))
        logger.info(
            "Classification: label=%s confidence=%.2f user=%s",
            result.predicted_label,
            result.confidence,
            user_id,
        )
        return result

    def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Extract structured data from text using the LLM provider."""
        import asyncio
        return asyncio.run(self._ai_use_cases.extract(
            text,
            fields=fields,
            system_prompt=system_prompt,
        ))

    def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> str:
        """Generate a summary of the given text."""
        import asyncio
        return asyncio.run(self._ai_use_cases.summarize(
            text,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        ))

    def generate_embeddings(
        self,
        document_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> list[EmbeddingDTO]:
        """Generate and store embeddings for a document's text content."""
        import asyncio
        results = asyncio.run(self._ai_use_cases.generate_embeddings(document_id))
        logger.info(
            "Embeddings generated: doc_id=%s count=%d",
            document_id,
            len(results),
        )
        return results

    def create_chat_session(
        self,
        user_id: uuid.UUID | None = None,
        title: str = "",
    ) -> dict[str, Any]:
        """Create a new chat session."""
        import uuid as _uuid
        session_id = _uuid.uuid4()
        return {
            "id": str(session_id),
            "user_id": str(user_id) if user_id else None,
            "title": title or f"Chat {session_id}",
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

    def get_chat_history(
        self,
        session_id: uuid.UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get chat history for a session."""
        return []

    def send_chat_message(
        self,
        session_id: uuid.UUID,
        message: str,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Send a message in a chat session."""
        return {
            "session_id": str(session_id),
            "user_message": message,
            "assistant_message": "Chat functionality requires LLM provider configuration.",
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
