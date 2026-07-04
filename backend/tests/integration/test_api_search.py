import pytest
from unittest.mock import patch, MagicMock

from rest_framework import status

from core.application.dtos.search_dto import SearchFiltersDTO, SearchQueryDTO, SearchResultDTO, SearchResponseDTO


@pytest.mark.django_db
class TestSearchEndpoint:
    """Tests for GET/POST /api/v1/search/search."""

    def test_search_get_with_query(self, auth_client):
        response = auth_client.get("/api/v1/search/search?q=test")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_get_without_query(self, auth_client):
        response = auth_client.get("/api/v1/search/search")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_post_hybrid(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {"query": "test document", "search_type": "hybrid"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_post_semantic(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {"query": "semantic search", "search_type": "semantic"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_post_keyword(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {"query": "keyword search", "search_type": "keyword"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_with_filters(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {
                "query": "invoice",
                "search_type": "hybrid",
                "filters": {
                    "doc_types": ["invoice", "receipt"],
                    "languages": ["en"],
                    "tags": ["important"],
                },
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_with_max_results(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {"query": "document", "search_type": "hybrid", "max_results": 5},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_with_offset(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {"query": "report", "search_type": "hybrid", "offset": 10},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/search/search?q=test")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_post_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/search/search",
            {"query": "test", "search_type": "hybrid"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_empty_query_post(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {"query": "", "search_type": "hybrid"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_invalid_search_type(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {"query": "test", "search_type": "invalid_type"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_with_date_filters(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {
                "query": "report",
                "search_type": "hybrid",
                "filters": {
                    "date_from": "2024-01-01T00:00:00Z",
                    "date_to": "2024-12-31T23:59:59Z",
                },
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_with_file_extensions(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/search",
            {
                "query": "document",
                "search_type": "keyword",
                "filters": {
                    "file_extensions": ["pdf", "txt"],
                },
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_search_get_with_query_params(self, auth_client):
        response = auth_client.get(
            "/api/v1/search/search?q=invoice&type=semantic&max_results=10&offset=0"
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestQuickSearchEndpoint:
    """Tests for GET/POST /api/v1/search/quick-search."""

    def test_quick_search_get(self, auth_client):
        response = auth_client.get("/api/v1/search/quick-search?q=meeting")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_quick_search_post(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/quick-search",
            {"query": "project report"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_quick_search_empty_query_get(self, auth_client):
        response = auth_client.get("/api/v1/search/quick-search?q=")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_quick_search_empty_query_post(self, auth_client):
        response = auth_client.post(
            "/api/v1/search/quick-search",
            {"query": ""},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_quick_search_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/search/quick-search?q=test")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_quick_search_post_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/search/quick-search",
            {"query": "test"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_quick_search_with_top_k(self, auth_client):
        response = auth_client.get("/api/v1/search/quick-search?q=report&top_k=5")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_quick_search_with_document_id(self, auth_client):
        import uuid
        response = auth_client.get(
            f"/api/v1/search/quick-search?q=report&document_id={uuid.uuid4()}"
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_quick_search_post_with_params(self, auth_client):
        import uuid
        response = auth_client.post(
            "/api/v1/search/quick-search",
            {"query": "report", "top_k": 3, "document_id": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]
