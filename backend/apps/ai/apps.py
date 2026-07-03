from django.apps import AppConfig


class AIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI"

    def ready(self) -> None:
        """Wire up AI service dependencies."""
        pass

    @property
    def ai_service(self):
        """Lazy initialization of AIService."""
        if not hasattr(self, "_ai_service"):
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

            llm_provider = StubLLMProvider()
            embedding_provider = StubEmbeddingProvider()

            use_cases = AIUseCases(
                ai_task_repository=DjangoAITaskRepository(),
                document_repository=DjangoDocumentRepository(),
                embedding_repository=DjangoEmbeddingRepository(),
                file_repository=DjangoFileRepository(),
                llm_provider=llm_provider,
                embedding_provider=embedding_provider,
            )
            self._ai_service = AIService(use_cases)
        return self._ai_service
