from __future__ import annotations

import logging
import uuid

from apps.chat.models import ChatMessage, ChatSession
from core.application.dtos.chat_dto import ChatMessageDTO, ChatResponseDTO, ChatSessionDTO
from core.application.use_cases.chat_use_cases import ChatUseCases

logger = logging.getLogger(__name__)


class ChatService:
    """Thin wrapper delegating chat operations to core ChatUseCases with ORM persistence."""

    def __init__(self, chat_use_cases: ChatUseCases) -> None:
        self._chat_use_cases = chat_use_cases

    async def create_session(
        self,
        user_id: uuid.UUID,
        title: str = "",
    ) -> ChatSessionDTO:
        """Create a new chat session and persist it."""
        result = await self._chat_use_cases.create_session(user_id, title=title)

        ChatSession.objects.create(
            id=result.id,
            user_id=user_id,
            title=result.title,
        )

        logger.info("Chat session created: %s by user %s", result.id, user_id)
        return result

    async def send_message(
        self,
        session_id: uuid.UUID,
        message: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> ChatResponseDTO:
        """Send a message, get AI response, and persist both."""
        response = await self._chat_use_cases.send_message(
            session_id,
            message,
            user_id=user_id,
        )

        # Persist user message
        ChatMessage.objects.update_or_create(
            id=uuid.uuid4(),
            defaults={
                "session_id": session_id,
                "role": ChatMessage.Role.USER,
                "content": message,
            },
        )

        # Persist assistant response
        ChatMessage.objects.update_or_create(
            id=response.message.id,
            defaults={
                "session_id": session_id,
                "role": ChatMessage.Role.ASSISTANT,
                "content": response.message.content,
                "sources": list(response.message.sources),
                "tokens_used": response.message.tokens_used,
                "model_used": response.message.model_used,
            },
        )

        # Update session timestamp
        ChatSession.objects.filter(id=session_id).update(
            title=response.message.content[:100] if not title_exists(session_id) else None,
        )

        logger.info(
            "Chat message sent: session=%s user=%s",
            session_id,
            user_id,
        )
        return response

    async def get_history(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ChatMessageDTO]:
        """Retrieve chat history, preferring ORM records."""
        messages = ChatMessage.objects.filter(
            session_id=session_id,
        ).order_by("-created_at")[:limit]

        return [
            ChatMessageDTO(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                sources=tuple(msg.sources) if isinstance(msg.sources, list) else (),
                tokens_used=msg.tokens_used,
                model_used=msg.model_used,
                created_at=msg.created_at,
            )
            for msg in reversed(messages)
        ]


def title_exists(session_id: uuid.UUID) -> bool:
    """Check if the session already has a non-empty title."""
    try:
        session = ChatSession.objects.get(id=session_id)
        return bool(session.title)
    except ChatSession.DoesNotExist:
        return False
