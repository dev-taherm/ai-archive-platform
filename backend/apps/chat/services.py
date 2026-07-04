from __future__ import annotations

import logging
import time
import uuid

from apps.chat.models import ChatMessage, ChatSession
from core.application.dtos.chat_dto import (
    ChatMessageDTO,
    ChatResponseDTO,
    ChatSessionDTO,
)

logger = logging.getLogger(__name__)


def _get_llm_provider():
    """Get the default LLM provider from database config."""
    try:
        from apps.ai.models import ProviderConfig
        from core.infrastructure.services.llm_factory import LLMFactory
        from core.domain.ai.value_objects import ModelConfig, AIProvider

        config = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["llm"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config:
            return None

        model_config = ModelConfig(
            provider=AIProvider(config.provider_type),
            model_name=config.model_name,
        )
        return LLMFactory.create(
            config.provider_type,
            model_config,
            api_key=config.api_key or None,
            base_url=config.base_url or None,
        )
    except Exception:
        logger.debug("Could not load LLM provider from config")
        return None


def _get_hybrid_search():
    """Get the hybrid search service for RAG context retrieval."""
    try:
        from core.infrastructure.services.hybrid_search import HybridSearchService
        from core.infrastructure.services.vector_store import VectorStore

        return HybridSearchService(vector_store=VectorStore())
    except Exception:
        logger.debug("Could not initialize hybrid search")
        return None


def _get_embedding_provider():
    """Get the default embedding provider for query embedding."""
    try:
        from apps.ai.models import ProviderConfig
        from core.infrastructure.services.embedding_service import (
            LangChainEmbeddingProvider,
        )

        config = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["embedding"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config:
            return None

        return LangChainEmbeddingProvider(
            model_name=config.model_name,
            provider=config.provider_type,
            api_key=config.api_key or None,
        )
    except Exception:
        logger.debug("Could not load embedding provider")
        return None


class ChatService:
    """Chat service with ORM persistence and RAG-powered LLM responses."""

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
        """Send a message, get RAG-augmented AI response, and persist both."""
        start = time.monotonic()

        # Persist user message
        ChatMessage.objects.create(
            session_id=session_id,
            role=ChatMessage.Role.USER,
            content=message,
        )

        # RAG: retrieve relevant document context
        context_text = self._retrieve_context(message)

        # Generate AI response
        response_text = self._generate_response(message, context_text)

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

    def _retrieve_context(self, query: str) -> str:
        """Retrieve relevant document chunks for RAG context."""
        try:
            search = _get_hybrid_search()
            embedding_provider = _get_embedding_provider()

            if not search or not embedding_provider:
                return ""

            query_embedding = embedding_provider.embed_text(query)
            results = search.search(
                query,
                query_embedding=query_embedding,
                top_k=5,
                threshold=0.3,
            )

            if not results:
                return ""

            context_parts = []
            for r in results:
                context_parts.append(r.text)

            return "\n\n---\n\n".join(context_parts)
        except Exception:
            logger.debug("RAG context retrieval failed")
            return ""

    def _generate_response(self, message: str, context: str) -> str:
        """Generate AI response using LLM with optional RAG context."""
        llm = _get_llm_provider()
        if llm is None:
            if context:
                return (
                    "I found relevant information in your documents, but no LLM "
                    "provider is configured to generate a response. Please configure "
                    "an AI provider in Settings.\n\n"
                    f"Relevant context:\n{context[:2000]}"
                )
            return (
                "No LLM provider is configured. Please set up an AI provider "
                "in Settings to enable chat functionality."
            )

        import asyncio

        system_prompt = (
            "You are an intelligent archive assistant. You help users search, "
            "understand, and manage their document archive. Be helpful, concise, "
            "and accurate. If you find relevant information in the provided context, "
            "use it to answer the user's question. If no context is provided, "
            "answer based on your general knowledge."
        )

        if context:
            system_prompt += f"\n\nRelevant document context:\n{context[:4000]}"

        messages = [{"role": "user", "content": message}]

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    response = pool.submit(
                        asyncio.run,
                        llm.chat(
                            messages,
                            system_prompt=system_prompt,
                            temperature=0.7,
                            max_tokens=2000,
                        ),
                    ).result(timeout=60)
            else:
                response = asyncio.run(
                    llm.chat(
                        messages,
                        system_prompt=system_prompt,
                        temperature=0.7,
                        max_tokens=2000,
                    )
                )
            return response
        except Exception:
            logger.exception("LLM chat failed")
            return (
                "I encountered an error while generating a response. "
                "Please check your AI provider configuration and try again."
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
