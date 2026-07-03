from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from core.application.dtos.chat_dto import ChatMessageDTO, ChatResponseDTO, ChatSessionDTO
from core.application.interfaces.repositories import DocumentRepository, EmbeddingRepository
from core.application.interfaces.services import EmbeddingProvider, LLMProvider

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """You are an AI archive assistant. Answer questions about archived
documents based on the provided context. Be concise and cite specific documents when
possible. If you cannot answer based on the context, say so."""


class ChatUseCases:
    """Use cases for conversational AI interactions over archived content."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_repository: EmbeddingRepository,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._document_repository = document_repository
        self._embedding_repository = embedding_repository
        self._llm_provider = llm_provider
        self._embedding_provider = embedding_provider
        self._sessions: dict[uuid.UUID, list[ChatMessageDTO]] = {}

    async def create_session(
        self,
        user_id: uuid.UUID,
        title: str = "",
    ) -> ChatSessionDTO:
        """Create a new chat session."""
        session_id = uuid.uuid4()
        self._sessions[session_id] = []

        return ChatSessionDTO(
            id=session_id,
            user_id=user_id,
            title=title or f"Chat {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            message_count=0,
        )

    async def send_message(
        self,
        session_id: uuid.UUID,
        message: str,
        *,
        user_id: uuid.UUID | None = None,
    ) -> ChatResponseDTO:
        """Send a message in a chat session and get a response with context."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        user_msg = ChatMessageDTO(
            session_id=session_id,
            role="user",
            content=message,
        )
        self._sessions[session_id].append(user_msg)

        context_chunks = await self._retrieve_context(message)

        context_text = "\n\n---\n\n".join(
            f"[Document: {c.get('title', 'Untitled')}]\n{c.get('content', '')}"
            for c in context_chunks
        ) if context_chunks else "No relevant documents found."

        messages_for_llm = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "system", "content": f"Context from archived documents:\n\n{context_text}"},
        ]

        history = self._sessions.get(session_id, [])
        for msg in history[-10:]:
            messages_for_llm.append({"role": msg.role, "content": msg.content})

        import time
        start = time.monotonic()

        response_text = await self._llm_provider.chat(
            messages_for_llm,
            temperature=0.3,
            max_tokens=2000,
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        references: list[ChatMessageDTO] = []
        sources: list[dict[str, Any]] = []
        for chunk in context_chunks:
            doc_id = chunk.get("document_id")
            if doc_id:
                sources.append({
                    "document_id": doc_id,
                    "title": chunk.get("title", ""),
                    "snippet": chunk.get("content", "")[:200],
                })

        assistant_msg = ChatMessageDTO(
            session_id=session_id,
            role="assistant",
            content=response_text,
            sources=tuple(sources),
        )
        self._sessions[session_id].append(assistant_msg)

        return ChatResponseDTO(
            message=assistant_msg,
            session_id=session_id,
            processing_time_ms=round(elapsed_ms, 2),
        )

    async def get_history(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ChatMessageDTO]:
        """Retrieve chat message history for a session."""
        messages = self._sessions.get(session_id, [])
        return messages[-limit:]

    async def _retrieve_context(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant document chunks for context."""
        try:
            query_embedding = await self._embedding_provider.embed_text(query)

            similar = await self._embedding_repository.search_similar(
                query_embedding,
                top_k=top_k,
                threshold=0.3,
            )

            context_chunks: list[dict[str, Any]] = []
            for vector_id, score, metadata in similar:
                context_chunks.append({
                    "document_id": metadata.get("document_id", ""),
                    "title": metadata.get("title", ""),
                    "content": metadata.get("content", ""),
                    "score": score,
                })

            return context_chunks

        except Exception as e:
            logger.warning("Failed to retrieve context: %s", e)
            return []
