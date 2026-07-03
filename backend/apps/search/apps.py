from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "Search"

    def ready(self) -> None:
        """Wire up Search service dependencies."""
        pass

    @property
    def search_service(self):
        """Lazy initialization of SearchService."""
        if not hasattr(self, "_search_service"):
            from apps.search.services import SearchService
            from core.infrastructure.db.repositories.document_repository import (
                DjangoDocumentRepository,
            )
            from core.infrastructure.db.repositories.ai_repository import (
                DjangoEmbeddingRepository,
            )
            from core.infrastructure.db.repositories.file_repository import (
                DjangoFileRepository,
            )
            from core.application.use_cases.search_use_cases import SearchUseCases
            from core.infrastructure.services.stub_providers import StubEmbeddingProvider

            embedding_provider = StubEmbeddingProvider()

            use_cases = SearchUseCases(
                document_repository=DjangoDocumentRepository(),
                embedding_repository=DjangoEmbeddingRepository(),
                file_repository=DjangoFileRepository(),
                embedding_provider=embedding_provider,
            )
            self._search_service = SearchService(use_cases)
        return self._search_service
