import pytest
from rest_framework import status


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_health_check(self, api_client):
        response = api_client.get("/health/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"
