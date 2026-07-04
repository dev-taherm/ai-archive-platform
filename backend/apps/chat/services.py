from __future__ import annotations

import logging
import time
import uuid

from apps.chat.models import ChatMessage, ChatSession
from core.application.dtos.chat_dto import ChatMessageDTO, ChatResponseDTO, ChatSessionDTO

logger = logging.getLogger(__name__)


class ChatService:
    """Chat service with ORM persistence for sessions and messages."""

    def __init__(self, chat_use_cases=None) -> None:
        self._chat_use_cases = chat_use_cases

    def create_session(
        self,
        user_id: uuid.UUID,
        title: str = "",
    ) -> ChatSessionDTO:
        """Create a new chat session and persist it."""
        session = ChatSession.objects.create(
            user_id=user_id,
            title=title or f"Chat {uuid.uuid4().hex[:8]}",
        )
        logger.info("Chat session created: %s by user %s", session.id, user_id)
        return ChatSessionDTO(
            id=session.id,
            user_id=user_id,
            title=session.title,
            message_count=0,
            created_at=session.created_at,
        )

    def send_message(
        self,
        session_id: uuid.UUID,
        message: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> ChatResponseDTO:
        """Send a message, get AI response, and persist both."""
        start = time.monotonic()

        # Persist user message
        ChatMessage.objects.create(
            session_id=session_id,
            role=ChatMessage.Role.USER,
            content=message,
        )

        # Get AI response (stub for now)
        response_text = "Chat functionality requires LLM provider configuration. Please set OPENAI_API_KEY or GOOGLE_API_KEY."

        elapsed_ms = (time.monotonic() - start) * 1000

        # Persist assistant response
        assistant_msg = ChatMessage.objects.create(
            session_id=session_id,
            role=ChatMessage.Role.ASSISTANT,
            content=response_text,
        )

        return ChatResponseDTO(
            message=ChatMessageDTO(
                id=assistant_msg.id,
                session_id=session_id,
                role="assistant",
                content=response_text,
            ),
            session_id=session_id,
            processing_time_ms=round(elapsed_ms, 2),
        )

    def get_history(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ChatMessageDTO]:
        """Retrieve chat history from ORM."""
        messages = ChatMessage.objects.filter(
            session_id=session_id,
        ).order_by("created_at")[:limit]

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
            for msg in messages
        ]

    def list_sessions(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[ChatSessionDTO]:
        """List chat sessions for a user."""
        sessions = ChatSession.objects.filter(
            user_id=user_id,
        ).order_by("-created_at")[:limit]

        return [
            ChatSessionDTO(
                id=s.id,
                user_id=user_id,
                title=s.title,
                message_count=s.messages.count(),
                created_at=s.created_at,
            )
            for s in sessions
        ]
