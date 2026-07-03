from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"
    verbose_name = "Documents"

    def ready(self) -> None:
        """Wire up Document service dependencies."""
        pass

    @property
    def document_service(self):
        """Lazy initialization of DocumentService."""
        if not hasattr(self, "_document_service"):
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
                StubEmbeddingProvider,
                StubLLMProvider,
                StubOCRProvider,
            )
            from core.infrastructure.services.document_reader import DocumentReader

            llm_provider = StubLLMProvider()
            ocr_provider = StubOCRProvider()

            use_cases = DocumentUseCases(
                document_repository=DjangoDocumentRepository(),
                file_repository=DjangoFileRepository(),
                embedding_repository=DjangoEmbeddingRepository(),
                ocr_provider=ocr_provider,
                llm_provider=llm_provider,
                document_reader=DocumentReader(),
            )
            self._document_service = DocumentService(use_cases)
        return self._document_service
