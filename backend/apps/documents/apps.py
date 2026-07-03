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
            StubEmbeddingProvider,
            StubLLMProvider,
        )
        from core.infrastructure.services.parser_router import ParserRouter
        from core.infrastructure.services.paddle_ocr_provider import PaddleOCRProvider

        llm_provider = StubLLMProvider()

        try:
            self._ocr_provider = PaddleOCRProvider(lang="ar", use_gpu=False)
        except Exception:
            logger.warning("PaddleOCR init failed, using stub")
            from core.infrastructure.services.stub_providers import StubOCRProvider
            self._ocr_provider = StubOCRProvider()

        use_cases = DocumentUseCases(
            document_repository=DjangoDocumentRepository(),
            file_repository=DjangoFileRepository(),
            embedding_repository=DjangoEmbeddingRepository(),
            ocr_provider=self._ocr_provider,
            llm_provider=llm_provider,
            document_reader=ParserRouter(),
        )
        self._document_service = DocumentService(use_cases)

    @property
    def document_service(self):
        """Lazy initialization of DocumentService."""
        self._ensure_wired()
        return self._document_service

    @property
    def ocr_provider(self):
        self._ensure_wired()
        return self._ocr_provider
