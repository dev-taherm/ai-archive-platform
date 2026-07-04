from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"
    verbose_name = "Chat"

    def ready(self) -> None:
        pass

    def _ensure_wired(self) -> None:
        if hasattr(self, "_chat_service"):
            return

        from apps.chat.services import ChatService
        from core.infrastructure.db.repositories.document_repository import (
            DjangoDocumentRepository,
        )
        from core.infrastructure.db.repositories.embedding_repository import (
            PgvectorEmbeddingRepository,
        )
        from core.application.use_cases.chat_use_cases import ChatUseCases
        from core.infrastructure.services.stub_providers import (
            StubEmbeddingProvider,
            StubLLMProvider,
        )

        use_cases = ChatUseCases(
            document_repository=DjangoDocumentRepository(),
            embedding_repository=PgvectorEmbeddingRepository(),
            llm_provider=StubLLMProvider(),
            embedding_provider=StubEmbeddingProvider(),
        )
        self._chat_service = ChatService(use_cases)

    @property
    def chat_service(self):
        self._ensure_wired()
        return self._chat_service
