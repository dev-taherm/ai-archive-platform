from django.apps import AppConfig


class FilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.files"
    verbose_name = "Files"

    def ready(self) -> None:
        """Wire up dependencies when Django starts."""
        pass

    @property
    def file_service(self):
        """Lazy initialization of FileService."""
        if not hasattr(self, "_file_service"):
            from apps.files.services import FileService
            from core.infrastructure.db.repositories.file_repository import (
                DjangoFileRepository,
            )
            from core.application.use_cases.file_use_cases import FileUseCases
            from core.infrastructure.services.file_scanner import FileScannerService
            from core.infrastructure.services.stub_providers import StubStorageBackend

            use_cases = FileUseCases(
                file_repository=DjangoFileRepository(),
                storage_backend=StubStorageBackend(),
                file_scanner=FileScannerService(),
            )
            self._file_service = FileService(use_cases)
        return self._file_service
