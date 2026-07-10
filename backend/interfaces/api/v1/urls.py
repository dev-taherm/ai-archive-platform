from django.urls import include, path
from rest_framework.routers import DefaultRouter

from interfaces.api.v1.views.auth_views import (
    LoginView,
    LogoutView,
    RegisterView,
    UserViewSet,
)
from interfaces.api.v1.views.file_views import FileRecordViewSet
from interfaces.api.v1.views.document_views import DocumentViewSet
from interfaces.api.v1.views.search_views import SearchView
from interfaces.api.v1.views.ai_views import AIView
from interfaces.api.v1.views.chat_views import ChatViewSet
from interfaces.api.v1.views.dashboard_views import DashboardView
from interfaces.api.v1.views.workflow_views import WorkflowViewSet
from interfaces.api.v1.views.report_views import ReportView
from interfaces.api.v1.views.provider_views import ProviderConfigViewSet
from interfaces.api.v1.views.tool_views import ToolViewSet
from apps.apikeys.views import ApiKeyViewSet
from apps.agents.views import AgentViewSet
from apps.organizations.views import InvitationViewSet, MembershipViewSet, OrganizationViewSet

router = DefaultRouter()
router.trailing_slash = ""

router.register(r"users", UserViewSet, basename="user")
router.register(r"files", FileRecordViewSet, basename="file")
router.register(r"documents", DocumentViewSet, basename="document")
router.register(r"ai", AIView, basename="ai")
router.register(r"chat", ChatViewSet, basename="chat")
router.register(r"dashboard", DashboardView, basename="dashboard")
router.register(r"workflows", WorkflowViewSet, basename="workflow")
router.register(r"reports", ReportView, basename="report")
router.register(r"search", SearchView, basename="search")
router.register(r"providers", ProviderConfigViewSet, basename="provider")
router.register(r"api-keys", ApiKeyViewSet, basename="api-key")
router.register(r"agents", AgentViewSet, basename="agent")
router.register(r"tools", ToolViewSet, basename="tool")
router.register(r"organizations", OrganizationViewSet, basename="organization")
router.register(r"memberships", MembershipViewSet, basename="membership")
router.register(r"invitations", InvitationViewSet, basename="invitation")

# Custom URL patterns for non-standard REST paths the frontend expects
urlpatterns = [
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/register", RegisterView.as_view({"post": "create"}), name="register"),
    path("auth/logout", LogoutView.as_view({"post": "create"}), name="logout"),
    path("reports/summary", ReportView.as_view({"get": "summary"}), name="report-summary"),
    path("", include(router.urls)),
]
