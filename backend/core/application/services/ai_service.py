from __future__ import annotations

import logging
import uuid
from typing import Any

from core.application.dtos.ai_dto import AIResultDTO, ClassificationDTO, EmbeddingDTO
from core.application.dtos.chat_dto import ChatMessageDTO, ChatResponseDTO, ChatSessionDTO
from core.application.interfaces.repositories import AuditLogRepository
from core.application.use_cases.ai_use_cases import AIUseCases
from core.application.use_cases.chat_use_cases import ChatUseCases
from core.domain.common.exceptions import ValidationException

logger = logging.getLogger(__name__)


class AIService:
    """Application service orchestrating AI and chat operations."""

    def __init__(
        self,
        ai_use_cases: AIUseCases,
        chat_use_cases: ChatUseCases,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._ai_use_cases = ai_use_cases
        self._chat_use_cases = chat_use_cases
        self._audit_log_repository = audit_log_repository

    async def classify(
        self,
        text: str,
        *,
        categories: list[str] | None = None,
        system_prompt: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ClassificationDTO:
        """Classify text content and log the operation."""
        result = await self._ai_use_cases.classify(
            text,
            categories=categories,
            system_prompt=system_prompt,
        )

        await self._audit(
            action="ai.classified",
            user_id=user_id,
            resource_type="ai",
            resource_id=None,
            details={
                "predicted_label": result.predicted_label,
                "confidence": result.confidence,
                "text_preview": result.input_text,
            },
        )

        return result

    async def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Extract structured data from text and log the operation."""
        result = await self._ai_use_cases.extract(
            text,
            fields=fields,
            system_prompt=system_prompt,
        )

        await self._audit(
            action="ai.extracted",
            user_id=user_id,
            resource_type="ai",
            resource_id=None,
            details={"fields": fields, "result_keys": list(result.keys())},
        )

        return result

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> str:
        """Summarize text content and log the operation."""
        result = await self._ai_use_cases.summarize(
            text,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )

        await self._audit(
            action="ai.summarized",
            user_id=user_id,
            resource_type="ai",
            resource_id=None,
            details={
                "text_length": len(text),
                "summary_length": len(result),
            },
        )

        return result

    async def generate_embeddings(
        self,
        document_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> list[EmbeddingDTO]:
        """Generate embeddings for a document and log the operation."""
        results = await self._ai_use_cases.generate_embeddings(document_id)

        await self._audit(
            action="ai.embeddings_generated",
            user_id=user_id,
            resource_type="document",
            resource_id=document_id,
            details={"embedding_count": len(results)},
        )

        return results

    async def create_chat_session(
        self,
        user_id: uuid.UUID,
        title: str = "",
    ) -> ChatSessionDTO:
        """Create a new chat session."""
        return await self._chat_use_cases.create_session(user_id, title=title)

    async def send_chat_message(
        self,
        session_id: uuid.UUID,
        message: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> ChatResponseDTO:
        """Send a chat message and return the response."""
        result = await self._chat_use_cases.send_message(
            session_id,
            message,
            user_id=user_id,
        )

        await self._audit(
            action="chat.message_sent",
            user_id=user_id,
            resource_type="chat_session",
            resource_id=session_id,
            details={
                "message_preview": message[:100],
                "response_preview": result.message.content[:100],
                "processing_time_ms": result.processing_time_ms,
            },
        )

        return result

    async def get_chat_history(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ChatMessageDTO]:
        """Retrieve chat history for a session."""
        return await self._chat_use_cases.get_history(session_id, limit=limit)

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
