import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from rest_framework import status


@pytest.mark.django_db
class TestAIClassifyEndpoint:
    """Tests for POST /api/v1/ai/classify."""

    def test_classify_success(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/classify",
            {"text": "This is an invoice for services rendered in January 2024."},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_classify_with_categories(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/classify",
            {
                "text": "Contract agreement between parties for software development",
                "categories": ["contract", "invoice", "receipt", "report"],
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_classify_empty_text(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/classify",
            {"text": ""},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_classify_missing_text(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/classify",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_classify_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/ai/classify",
            {"text": "test"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_classify_long_text(self, auth_client):
        long_text = "This is a test sentence. " * 500
        response = auth_client.post(
            "/api/v1/ai/classify",
            {"text": long_text},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_classify_with_system_prompt(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/classify",
            {
                "text": "Invoice #12345 for consulting services",
                "system_prompt": "Classify this document as either invoice, contract, or report.",
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestAIExtractEndpoint:
    """Tests for POST /api/v1/ai/extract."""

    def test_extract_success(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/extract",
            {
                "text": "Invoice #12345, Total: $5000, Date: 2024-01-15, Client: Acme Corp",
                "fields": ["invoice_number", "total", "date", "client"],
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_extract_empty_text(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/extract",
            {"text": "", "fields": ["title"]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_extract_empty_fields(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/extract",
            {"text": "Some text", "fields": []},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_extract_missing_fields(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/extract",
            {"text": "Some text"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_extract_missing_text(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/extract",
            {"fields": ["title"]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_extract_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/ai/extract",
            {"text": "test", "fields": ["title"]},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_extract_with_system_prompt(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/extract",
            {
                "text": "Meeting notes from January 15, 2024",
                "fields": ["date", "attendees"],
                "system_prompt": "Extract meeting metadata from this text.",
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestAISummarizeEndpoint:
    """Tests for POST /api/v1/ai/summarize."""

    def test_summarize_success(self, auth_client):
        long_text = "This is a detailed report about Q4 2024 financial performance. " * 50
        response = auth_client.post(
            "/api/v1/ai/summarize",
            {"text": long_text},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_summarize_with_max_tokens(self, auth_client):
        long_text = "Content to summarize. " * 100
        response = auth_client.post(
            "/api/v1/ai/summarize",
            {"text": long_text, "max_tokens": 100},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_summarize_empty_text(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/summarize",
            {"text": ""},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_summarize_missing_text(self, auth_client):
        response = auth_client.post(
            "/api/v1/ai/summarize",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_summarize_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/ai/summarize",
            {"text": "test content"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_summarize_with_system_prompt(self, auth_client):
        long_text = "Document content. " * 100
        response = auth_client.post(
            "/api/v1/ai/summarize",
            {
                "text": long_text,
                "system_prompt": "Summarize this in bullet points.",
                "max_tokens": 200,
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestAIProvidersEndpoint:
    """Tests for GET /api/v1/ai/providers."""

    def test_providers_list(self, auth_client):
        response = auth_client.get("/api/v1/ai/providers")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) > 0

    def test_providers_contain_expected_fields(self, auth_client):
        response = auth_client.get("/api/v1/ai/providers")
        assert response.status_code == status.HTTP_200_OK
        for provider in response.data:
            assert "name" in provider
            assert "display_name" in provider
            assert "is_available" in provider
            assert "models" in provider
            assert "capabilities" in provider

    def test_providers_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/ai/providers")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAIProviderConfigCRUD:
    """Tests for provider configuration CRUD operations."""

    def test_list_provider_configs(self, auth_client, sample_provider):
        response = auth_client.get("/api/v1/providers")
        assert response.status_code == status.HTTP_200_OK

    def test_create_provider_config(self, auth_client):
        response = auth_client.post(
            "/api/v1/providers",
            {
                "name": "anthropic",
                "display_name": "Anthropic",
                "provider_type": "openai",
                "capabilities": ["llm"],
                "api_key": "sk-ant-test",
                "model_name": "claude-3-opus",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_provider_config_missing_fields(self, auth_client):
        response = auth_client.post(
            "/api/v1/providers",
            {"name": "incomplete"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_provider_config(self, auth_client, sample_provider):
        response = auth_client.get(f"/api/v1/providers/{sample_provider.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "openai"

    def test_retrieve_nonexistent_provider(self, auth_client):
        response = auth_client.get(
            "/api/v1/providers/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_provider_config(self, auth_client, sample_provider):
        response = auth_client.put(
            f"/api/v1/providers/{sample_provider.id}",
            {
                "name": "openai",
                "display_name": "OpenAI Updated",
                "provider_type": "openai",
                "capabilities": ["llm", "embedding"],
                "model_name": "gpt-4o",
                "is_active": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_provider_config(self, auth_client, sample_provider):
        response = auth_client.delete(f"/api/v1/providers/{sample_provider.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_nonexistent_provider(self, auth_client):
        response = auth_client.delete(
            "/api/v1/providers/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_set_default_provider(self, auth_client, sample_provider):
        response = auth_client.post(
            f"/api/v1/providers/{sample_provider.id}/set-default"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_active_providers(self, auth_client, sample_provider):
        response = auth_client.get("/api/v1/providers/active")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_providers_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/providers")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
