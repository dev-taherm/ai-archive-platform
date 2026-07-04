import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAuthEndpoints:
    def test_register(self, api_client):
        response = api_client.post("/api/v1/auth/register", {
            "email": "new@example.com",
            "password": "securepass123",
            "password_confirm": "securepass123",
            "username": "newuser",
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_login(self, api_client, test_user):
        response = api_client.post("/api/v1/auth/login", {
            "email": "test@example.com",
            "password": "testpass123",
        })
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_unauthenticated_access(self, api_client):
        response = api_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_access(self, auth_client):
        response = auth_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_200_OK
