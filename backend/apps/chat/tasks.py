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
    from apps.chat.services import ChatService

    service = ChatService()
    response = service.send_message(
        uuid.UUID(session_id),
        message,
        user_id=uuid.UUID(user_id) if user_id else None,
    )

    return {
        "response": response.message.content[:200],
        "processing_time_ms": response.processing_time_ms,
        "session_id": str(response.session_id),
    }
