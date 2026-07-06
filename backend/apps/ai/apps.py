from django.apps import AppConfig


class AIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI"

    def ready(self) -> None:
        """Wire up AI service dependencies."""
        pass

    def _ensure_wired(self) -> None:
        """Lazily wire dependencies on first access."""
        if hasattr(self, "_ai_service"):
            return

        import os
        import logging

        from apps.ai.services import AIService
        from core.infrastructure.db.repositories.ai_repository import (
            DjangoAITaskRepository,
            DjangoEmbeddingRepository,
        )
        from core.infrastructure.db.repositories.document_repository import (
            DjangoDocumentRepository,
        )
        from core.infrastructure.db.repositories.file_repository import (
            DjangoFileRepository,
        )
        from core.application.use_cases.ai_use_cases import AIUseCases
        from core.infrastructure.services.stub_providers import (
            StubEmbeddingProvider,
            StubLLMProvider,
        )
        from core.infrastructure.services.llm_factory import LLMFactory
        from core.domain.ai.value_objects import AIProvider, ModelConfig

        logger = logging.getLogger(__name__)

        # Try to load from database first
        llm_provider = None
        embedding_provider = None

        try:
            from apps.ai.models import ProviderConfig

            default_llm = (
                ProviderConfig.objects.filter(
                    is_active=True, capabilities__contains="llm", is_default=True
                ).first()
            )
            if default_llm:
                config = ModelConfig(
                    model_name=default_llm.model_name
                    or os.environ.get("DEFAULT_LLM_MODEL", "gpt-4o"),
                    provider=AIProvider(default_llm.provider_type),
                )
                llm_provider = LLMFactory.create(
                    default_llm.provider_type,
                    config,
                    api_key=default_llm.api_key or None,
                    base_url=default_llm.base_url or None,
                )

            default_emb = (
                ProviderConfig.objects.filter(
                    is_active=True,
                    capabilities__contains="embedding",
                    is_default=True,
                ).first()
            )
            if default_emb:
                from core.infrastructure.services.embedding_service import (
                    LangChainEmbeddingProvider,
                )

                embedding_provider = LangChainEmbeddingProvider(
                    model_name=default_emb.model_name or "ibm-granite/granite-embedding-97m-multilingual-r2",
                    provider=default_emb.provider_type,
                )
        except Exception as e:
            logger.warning("Failed to load provider config from DB: %s", e)

        # Fallback to stubs
        if llm_provider is None:
            llm_provider = StubLLMProvider()
        if embedding_provider is None:
            # Default to local multilingual embedding model (no API key needed)
            from core.infrastructure.services.embedding_service import FastEmbedProvider

            try:
                embedding_provider = FastEmbedProvider()
                logger.info(
                    "Using default local embedding model: %s",
                    FastEmbedProvider.DEFAULT_MODEL,
                )
            except Exception as e:
                logger.warning(
                    "Failed to load local embedding model, falling back to stub: %s",
                    e,
                )
                embedding_provider = StubEmbeddingProvider()

        self._llm_provider = llm_provider
        self._embedding_provider = embedding_provider

        use_cases = AIUseCases(
            ai_task_repository=DjangoAITaskRepository(),
            document_repository=DjangoDocumentRepository(),
            embedding_repository=DjangoEmbeddingRepository(),
            file_repository=DjangoFileRepository(),
            llm_provider=self._llm_provider,
            embedding_provider=self._embedding_provider,
        )
        self._ai_service = AIService(use_cases)

    def refresh_providers(self) -> None:
        """Force re-wire of providers (call after config changes)."""
        if hasattr(self, "_ai_service"):
            del self._ai_service
        if hasattr(self, "_llm_provider"):
            del self._llm_provider
        if hasattr(self, "_embedding_provider"):
            del self._embedding_provider
        self._ensure_wired()

    @property
    def ai_service(self):
        """Lazy initialization of AIService."""
        self._ensure_wired()
        return self._ai_service

    @property
    def llm_provider(self):
        self._ensure_wired()
        return self._llm_provider

    @property
    def embedding_provider(self):
        self._ensure_wired()
        return self._embedding_provider
