from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from apps.chat.models import ChatMessage, ChatSession
from core.application.dtos.chat_dto import (
    ChatMessageDTO,
    ChatResponseDTO,
    ChatSessionDTO,
)

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5


def _get_llm_provider():
    """Get the default LLM provider from database config."""
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
    """Get the default embedding provider for query embedding.

    Priority:
    1. DB ProviderConfig with embedding capability
    2. Local fastembed model (granite-embedding-97m-multilingual-r2)
    3. None (caller handles gracefully)
    """
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

        if config:
            return LangChainEmbeddingProvider(
                model_name=config.model_name,
                provider=config.provider_type,
                api_key=config.api_key or None,
            )

        # Fallback to local multilingual embedding model
        from core.infrastructure.services.embedding_service import FastEmbedProvider

        return FastEmbedProvider()
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

        # Load conversation history for multi-turn tool-calling context
        history = self._load_history(session_id)

        # Generate AI response with tool-calling loop
        response_text, tool_calls_data = self._generate_response(
            message, context_text, history
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        # Persist assistant response with tool calls
        assistant_msg = ChatMessage.objects.create(
            session_id=session_id,
            role=ChatMessage.Role.ASSISTANT,
            content=response_text,
            tool_calls=tool_calls_data,
        )

        return ChatResponseDTO(
            message=ChatMessageDTO(
                id=assistant_msg.id,
                session_id=session_id,
                role="assistant",
                content=response_text,
                tool_calls=tuple(tool_calls_data) if tool_calls_data else (),
            ),
            session_id=session_id,
            processing_time_ms=round(elapsed_ms, 2),
        )

    def _retrieve_context(self, query: str) -> str:
        """Retrieve relevant document chunks for RAG context.

        Tries semantic + keyword search first. Falls back to keyword-only
        search when embedding provider is unavailable or fails.
        """
        try:
            search = _get_hybrid_search()

            if not search:
                return ""

            query_embedding = None
            embedding_provider = _get_embedding_provider()
            if embedding_provider:
                try:
                    query_embedding = embedding_provider.embed_text(query)
                except Exception as e:
                    logger.warning(
                        "Embedding failed, falling back to keyword search: %s", e
                    )

            results = search.search(
                query,
                query_embedding=query_embedding,
                top_k=5,
                threshold=0.0 if query_embedding is None else 0.3,
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

    def _load_history(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Load recent conversation history as message dicts for the LLM.

        Returns list of {"role": ..., "content": ...} dicts suitable for
        passing to chat_with_tools(). Tool call messages are included as
        assistant messages with tool_calls, and tool results as tool role
        messages.
        """
        messages = ChatMessage.objects.filter(
            session_id=session_id,
        ).order_by("created_at")[-limit:]

        history: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "user":
                history.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    entry["tool_calls"] = msg.tool_calls
                history.append(entry)
            elif msg.role == "tool":
                history.append({
                    "role": "tool",
                    "tool_call_id": msg.metadata.get("tool_call_id", ""),
                    "content": msg.content,
                })

        return history

    def _generate_response(
        self,
        message: str,
        context: str,
        history: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Generate AI response using LLM with tool-calling loop.

        Returns:
            Tuple of (response_text, tool_calls_data) where tool_calls_data
            is a list of dicts describing each tool call made during generation.
        """
        try:
            llm = _get_llm_provider()
        except Exception as e:
            logger.exception("Failed to load LLM provider")
            return (
                f"Failed to load AI provider: {type(e).__name__}: {e}\n\n"
                "Please check your AI provider configuration in Settings.",
                [],
            )

        if llm is None:
            if context:
                return (
                    "I found relevant information in your documents, but no LLM "
                    "provider is configured to generate a response. Please configure "
                    "an AI provider in Settings.\n\n"
                    f"Relevant context:\n{context[:2000]}",
                    [],
                )
            return (
                "No LLM provider is configured. Please set up an AI provider "
                "in Settings to enable chat functionality.",
                [],
            )

        # Import tool registry
        from core.application.tools import registry

        system_prompt = (
            "You are an intelligent archive assistant. You help users search, "
            "understand, and manage their document archive. Be helpful, concise, "
            "and accurate. If you find relevant information in the provided context, "
            "use it to answer the user's question. If no context is provided, "
            "answer based on your general knowledge.\n\n"
            "You have access to tools for searching documents, managing agents, "
            "running workflows, and updating document metadata. Use tools when "
            "the user asks you to perform actions or needs specific information "
            "from the archive. Always explain what you're doing before and after "
            "using a tool."
        )

        if context:
            system_prompt += f"\n\nRelevant document context:\n{context[:4000]}"

        # Build message list: history + current user message
        messages: list[dict[str, str]] = []
        if history:
            for h in history:
                # For the LLM, flatten tool calls into content
                if h["role"] == "assistant" and "tool_calls" in h:
                    # Include tool call info in the message for context
                    tc_desc = []
                    for tc in h["tool_calls"]:
                        tc_desc.append(f"[Called tool: {tc.get('name', '?')}]")
                    combined = h.get("content", "") + " " + " ".join(tc_desc)
                    messages.append({"role": "assistant", "content": combined.strip()})
                elif h["role"] == "tool":
                    # Include tool result as context
                    messages.append({
                        "role": "user",
                        "content": f"[Tool result]: {h.get('content', '')}",
                    })
                elif h["role"] in ("user", "assistant"):
                    messages.append({
                        "role": h["role"],
                        "content": h.get("content", ""),
                    })

        messages.append({"role": "user", "content": message})

        # Get tool definitions (only if registry has tools)
        tool_defs = registry.get_definitions() if registry.tool_names else None

        # Tool-calling loop
        all_tool_calls: list[dict[str, Any]] = []
        final_content = ""

        try:
            import asyncio

            loop = None
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop = None
            except RuntimeError:
                loop = None

            for iteration in range(MAX_TOOL_ITERATIONS):
                if loop is None:
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(
                            asyncio.run,
                            llm.chat_with_tools(
                                messages,
                                system_prompt=system_prompt,
                                temperature=0.7,
                                max_tokens=2000,
                                tools=tool_defs,
                            ),
                        ).result(timeout=120)
                else:
                    result = loop.run_until_complete(
                        llm.chat_with_tools(
                            messages,
                            system_prompt=system_prompt,
                            temperature=0.7,
                            max_tokens=2000,
                            tools=tool_defs,
                        )
                    )

                # No tool calls — we have the final response
                if not result.tool_calls:
                    final_content = result.content
                    break

                # Process tool calls
                # Add assistant message with tool calls to context
                assistant_entry: dict[str, Any] = {"role": "assistant", "content": result.content}
                messages.append(assistant_entry)

                for tc in result.tool_calls:
                    logger.info(
                        "Tool call: %s(%s) [iteration %d/%d]",
                        tc.name,
                        json.dumps(tc.arguments)[:200],
                        iteration + 1,
                        MAX_TOOL_ITERATIONS,
                    )

                    # Execute the tool
                    import asyncio as _asyncio

                    if loop is None:
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            tool_result = pool.submit(
                                _asyncio.run,
                                registry.execute(tc.name, tc.arguments),
                            ).result(timeout=30)
                    else:
                        tool_result = loop.run_until_complete(
                            registry.execute(tc.name, tc.arguments)
                        )

                    result_text = tool_result.get("result", str(tool_result))
                    all_tool_calls.append({
                        "id": tc.id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                        "result": result_text,
                    })

                    # Add tool result to messages for next iteration
                    messages.append({
                        "role": "user",
                        "content": f"[Tool result for {tc.name}]: {result_text[:3000]}",
                    })

                # If we've done max iterations, generate a final text response
                if iteration == MAX_TOOL_ITERATIONS - 1:
                    if loop is None:
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            final_result = pool.submit(
                                asyncio.run,
                                llm.chat(
                                    messages,
                                    system_prompt=system_prompt,
                                    temperature=0.7,
                                    max_tokens=2000,
                                ),
                            ).result(timeout=60)
                    else:
                        final_result = loop.run_until_complete(
                            llm.chat(
                                messages,
                                system_prompt=system_prompt,
                                temperature=0.7,
                                max_tokens=2000,
                            )
                        )
                    final_content = final_result

            if not final_content:
                final_content = "I was unable to generate a response."

            return final_content, all_tool_calls

        except Exception as e:
            logger.exception("LLM chat failed")
            error_type = type(e).__name__
            error_msg = str(e)
            return (
                f"AI provider error ({error_type}): {error_msg}\n\n"
                "Please verify your AI provider settings (API key, base URL, "
                "model name) are correct.",
                all_tool_calls,
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
                tool_calls=tuple(msg.tool_calls) if isinstance(msg.tool_calls, list) else (),
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
