import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"
    verbose_name = "Documents"

    def ready(self) -> None:
        """Wire up Document service dependencies."""
        pass

    def _ensure_wired(self) -> None:
        """Lazily wire dependencies on first access."""
        if hasattr(self, "_document_service"):
            return

        from apps.documents.services import DocumentService
        from core.infrastructure.db.repositories.document_repository import (
            DjangoDocumentRepository,
        )
        from core.infrastructure.db.repositories.file_repository import (
            DjangoFileRepository,
        )
        from core.infrastructure.db.repositories.ai_repository import (
            DjangoEmbeddingRepository,
        )
        from core.application.use_cases.document_use_cases import DocumentUseCases
        from core.infrastructure.services.stub_providers import (
            StubLLMProvider,
        )

        llm_provider = StubLLMProvider()

        use_cases = DocumentUseCases(
            document_repository=DjangoDocumentRepository(),
            file_repository=DjangoFileRepository(),
            embedding_repository=DjangoEmbeddingRepository(),
            llm_provider=llm_provider,
        )
        self._document_service = DocumentService(use_cases)

    @property
    def document_service(self):
        """Lazy initialization of DocumentService."""
        self._ensure_wired()
        return self._document_service
