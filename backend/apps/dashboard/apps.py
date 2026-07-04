from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    verbose_name = "Dashboard"

    def ready(self) -> None:
        pass

    def _ensure_wired(self) -> None:
        if hasattr(self, "_dashboard_service"):
            return
        from apps.dashboard.services import DashboardService
        self._dashboard_service = DashboardService()

    @property
    def dashboard_service(self):
        self._ensure_wired()
        return self._dashboard_service
