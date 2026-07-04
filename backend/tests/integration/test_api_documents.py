import pytest
from rest_framework import status


@pytest.mark.django_db
class TestDocumentEndpoints:
    def test_list_documents(self, auth_client):
        response = auth_client.get("/api/v1/documents")
        assert response.status_code == status.HTTP_200_OK

    def test_list_documents_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/documents")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
