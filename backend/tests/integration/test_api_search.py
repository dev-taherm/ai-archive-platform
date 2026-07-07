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


@pytest.mark.django_db
class TestSearchHistoryEndpoint:
    """Tests for GET /api/v1/search/history."""

    def test_history_empty(self, auth_client):
        resp = auth_client.get("/api/v1/search/history")
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_history_with_log(self, auth_client, sample_search_log):
        resp = auth_client.get("/api/v1/search/history")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_history_limit(self, auth_client, sample_search_log):
        resp = auth_client.get("/api/v1/search/history?limit=1")
        assert resp.status_code == 200

    def test_history_unauthenticated(self, api_client):
        resp = api_client.get("/api/v1/search/history")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestSavedSearchEndpoint:
    """Tests for GET/POST/DELETE /api/v1/search/saved."""

    def test_list_saved_empty(self, auth_client):
        resp = auth_client.get("/api/v1/search/saved")
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_list_saved_with_data(self, auth_client, sample_saved_search):
        resp = auth_client.get("/api/v1/search/saved")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["name"] == "My Search"

    def test_create_saved_search(self, auth_client):
        resp = auth_client.post(
            "/api/v1/search/saved",
            {"name": "My Search", "query": "invoice 2024", "search_type": "hybrid"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["name"] == "My Search"

    def test_create_saved_search_missing_fields(self, auth_client):
        resp = auth_client.post("/api/v1/search/saved", {}, format="json")
        assert resp.status_code == 400

    def test_delete_saved_search(self, auth_client, sample_saved_search):
        resp = auth_client.delete(
            f"/api/v1/search/saved?id={sample_saved_search.id}"
        )
        assert resp.status_code == 204

    def test_delete_saved_search_not_found(self, auth_client):
        import uuid
        resp = auth_client.delete(
            f"/api/v1/search/saved?id={uuid.uuid4()}"
        )
        assert resp.status_code == 404

    def test_saved_search_unauthenticated(self, api_client):
        resp = api_client.get("/api/v1/search/saved")
        assert resp.status_code == 401
