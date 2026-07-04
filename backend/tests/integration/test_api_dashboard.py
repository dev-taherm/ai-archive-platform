import pytest
from rest_framework import status


@pytest.mark.django_db
class TestDashboardStatsEndpoint:
    """Tests for GET /api/v1/dashboard/stats."""

    def test_stats_success(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/stats")
        assert response.status_code == status.HTTP_200_OK

    def test_stats_contains_expected_fields(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/stats")
        assert response.status_code == status.HTTP_200_OK
        assert "total_files" in response.data
        assert "total_documents" in response.data
        assert "total_searches" in response.data
        assert "total_chat_sessions" in response.data
        assert "files_by_status" in response.data
        assert "documents_by_type" in response.data
        assert "documents_by_status" in response.data
        assert "recent_uploads_count" in response.data
        assert "storage_used_bytes" in response.data
        assert "avg_processing_time_ms" in response.data

    def test_stats_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/dashboard/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_stats_with_data(self, auth_client, sample_file_record, sample_document):
        response = auth_client.get("/api/v1/dashboard/stats")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data["total_files"], int)
        assert isinstance(response.data["total_documents"], int)

    def test_stats_values_are_non_negative(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/stats")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_files"] >= 0
        assert response.data["total_documents"] >= 0
        assert response.data["total_searches"] >= 0
        assert response.data["total_chat_sessions"] >= 0
        assert response.data["storage_used_bytes"] >= 0


@pytest.mark.django_db
class TestDashboardChartsEndpoint:
    """Tests for GET /api/v1/dashboard/charts."""

    def test_charts_success(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/charts")
        assert response.status_code == status.HTTP_200_OK

    def test_charts_returns_list(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/charts")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_charts_has_four_charts(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/charts")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 4

    def test_charts_with_period_7d(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/charts?period=7d")
        assert response.status_code == status.HTTP_200_OK

    def test_charts_with_period_30d(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/charts?period=30d")
        assert response.status_code == status.HTTP_200_OK

    def test_charts_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/dashboard/charts")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_charts_contain_expected_fields(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/charts")
        assert response.status_code == status.HTTP_200_OK
        for chart in response.data:
            assert "chart_type" in chart
            assert "title" in chart
            assert "data" in chart
            assert "period" in chart

    def test_charts_types_are_valid(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/charts")
        assert response.status_code == status.HTTP_200_OK
        valid_types = {"line", "bar", "pie", "area"}
        for chart in response.data:
            assert chart["chart_type"] in valid_types

    def test_charts_with_data(self, auth_client, sample_file_record, sample_document):
        response = auth_client.get("/api/v1/dashboard/charts?period=30d")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 4


@pytest.mark.django_db
class TestDashboardActivityEndpoint:
    """Tests for GET /api/v1/dashboard/activity."""

    def test_activity_success(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/activity")
        assert response.status_code == status.HTTP_200_OK

    def test_activity_contains_expected_fields(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/activity")
        assert response.status_code == status.HTTP_200_OK
        assert "activities" in response.data
        assert "total_count" in response.data

    def test_activity_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/dashboard/activity")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_activity_with_limit(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/activity?limit=5")
        assert response.status_code == status.HTTP_200_OK

    def test_activity_with_offset(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/activity?offset=0&limit=10")
        assert response.status_code == status.HTTP_200_OK

    def test_activity_with_high_limit(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/activity?limit=100")
        assert response.status_code == status.HTTP_200_OK

    def test_activity_activities_is_list(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/activity")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data["activities"], list)

    def test_activity_total_count_is_int(self, auth_client):
        response = auth_client.get("/api/v1/dashboard/activity")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data["total_count"], int)

    def test_activity_with_audit_log(self, auth_client, test_user, sample_file_record):
        from apps.files.models import AuditLog
        AuditLog.objects.create(
            user=test_user,
            action="upload",
            resource_type="file",
            resource_id=str(sample_file_record.id),
            details={"filename": "test.pdf"},
        )
        response = auth_client.get("/api/v1/dashboard/activity")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] >= 1
