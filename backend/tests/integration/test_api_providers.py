import pytest
from rest_framework import status


@pytest.mark.django_db
class TestProviderEndpoints:
    """Comprehensive tests for AI Provider config API endpoints."""

    def test_list_providers(self, auth_client):
        response = auth_client.get("/api/v1/providers")
        assert response.status_code == status.HTTP_200_OK

    def test_create_provider(self, auth_client):
        response = auth_client.post(
            "/api/v1/providers",
            {
                "name": "test-openai",
                "display_name": "Test OpenAI",
                "provider_type": "openai",
                "capabilities": ["llm", "embedding"],
                "api_key": "sk-test-key",
                "model_name": "gpt-4o",
                "is_active": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_provider_ollama(self, auth_client):
        response = auth_client.post(
            "/api/v1/providers",
            {
                "name": "local-ollama",
                "display_name": "Local Ollama",
                "provider_type": "ollama",
                "capabilities": ["llm"],
                "base_url": "http://localhost:11434",
                "model_name": "llama3.1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_set_default_provider(self, auth_client):
        # Create a provider
        create_response = auth_client.post(
            "/api/v1/providers",
            {
                "name": "default-test",
                "display_name": "Default Test",
                "provider_type": "openai",
                "capabilities": ["llm"],
                "model_name": "gpt-4o",
            },
            format="json",
        )
        provider_id = create_response.data["id"]

        response = auth_client.post(f"/api/v1/providers/{provider_id}/set-default")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
        ]

    def test_list_active_providers(self, auth_client):
        response = auth_client.get("/api/v1/providers/active")
        assert response.status_code == status.HTTP_200_OK
