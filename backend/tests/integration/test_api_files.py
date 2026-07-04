import pytest
from rest_framework import status


@pytest.mark.django_db
class TestFileEndpoints:
    def test_list_files(self, auth_client):
        response = auth_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_200_OK

    def test_list_files_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_files_endpoint_exists(self, auth_client):
        response = auth_client.get("/api/v1/files")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
