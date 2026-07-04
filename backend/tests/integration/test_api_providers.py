import pytest
from rest_framework import status


@pytest.mark.django_db
class TestProviderEndpoints:
    def test_list_providers(self, auth_client):
        response = auth_client.get("/api/v1/providers")
        assert response.status_code == status.HTTP_200_OK

    def test_create_provider(self, auth_client):
        response = auth_client.post("/api/v1/providers", {
            "name": "test-openai",
            "display_name": "Test OpenAI",
            "provider_type": "openai",
            "capabilities": ["llm"],
            "model_name": "gpt-4o",
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_providers_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/providers")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
