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

        self._llm_provider = StubLLMProvider()
        self._embedding_provider = StubEmbeddingProvider()

        use_cases = AIUseCases(
            ai_task_repository=DjangoAITaskRepository(),
            document_repository=DjangoDocumentRepository(),
            embedding_repository=DjangoEmbeddingRepository(),
            file_repository=DjangoFileRepository(),
            llm_provider=self._llm_provider,
            embedding_provider=self._embedding_provider,
        )
        self._ai_service = AIService(use_cases)

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
