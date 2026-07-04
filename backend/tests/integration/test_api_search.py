import pytest
from rest_framework import status


@pytest.mark.django_db
class TestSearchEndpoints:
    def test_search_endpoint(self, auth_client):
        response = auth_client.get("/api/v1/search/search?q=test")
        assert response.status_code == status.HTTP_200_OK

    def test_search_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/search/search?q=test")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
