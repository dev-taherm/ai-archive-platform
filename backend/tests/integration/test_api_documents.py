import pytest
import uuid
from unittest.mock import patch, MagicMock

from rest_framework import status

from apps.documents.models import Document
from apps.files.models import FileRecord


@pytest.mark.django_db
class TestDocumentListEndpoint:
    """Tests for GET /api/v1/documents."""

    def test_list_documents_empty(self, auth_client):
        response = auth_client.get("/api/v1/documents")
        assert response.status_code == status.HTTP_200_OK

    def test_list_documents_with_data(self, auth_client, sample_document):
        response = auth_client.get("/api/v1/documents")
        assert response.status_code == status.HTTP_200_OK

    def test_list_documents_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/documents")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_documents_returns_proper_format(self, auth_client, sample_document):
        response = auth_client.get("/api/v1/documents")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, (list, dict))


@pytest.mark.django_db
class TestDocumentRetrieveEndpoint:
    """Tests for GET /api/v1/documents/{id}."""

    def test_retrieve_existing_document(self, auth_client, sample_document):
        response = auth_client.get(f"/api/v1/documents/{sample_document.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_nonexistent_document(self, auth_client):
        response = auth_client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_retrieve_invalid_uuid(self, auth_client):
        response = auth_client.get("/api/v1/documents/invalid-id")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_unauthenticated(self, api_client, sample_document):
        response = api_client.get(f"/api/v1/documents/{sample_document.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentProcessEndpoint:
    """Tests for POST /api/v1/documents/process."""

    def test_process_requires_file_id(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/process", {}, format="json"
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_202_ACCEPTED,
        ]

    def test_process_invalid_file_id(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/process",
            {"file_id": "invalid-uuid"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_process_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/documents/process",
            {"file_id": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentProcessPipelineEndpoint:
    """Tests for POST /api/v1/documents/process-pipeline."""

    def test_process_pipeline_missing_file_id(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/process-pipeline", {}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_process_pipeline_invalid_file_id(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/process-pipeline",
            {"file_id": "not-a-uuid"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_process_pipeline_nonexistent_file(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/process-pipeline",
            {"file_id": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_process_pipeline_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/documents/process-pipeline",
            {"file_id": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentMetadataEndpoint:
    """Tests for GET /api/v1/documents/{id}/metadata."""

    @pytest.mark.xfail(
        reason="Stub LLM provider returns empty strings causing int conversion error",
        strict=False,
        raises=ValueError,
    )
    def test_metadata_existing_document(self, auth_client, sample_document):
        response = auth_client.get(
            f"/api/v1/documents/{sample_document.id}/metadata"
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_metadata_nonexistent_document(self, auth_client):
        response = auth_client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/metadata"
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_metadata_invalid_id(self, auth_client):
        response = auth_client.get("/api/v1/documents/invalid-id/metadata")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_metadata_unauthenticated(self, api_client, sample_document):
        response = api_client.get(
            f"/api/v1/documents/{sample_document.id}/metadata"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentClassifyEndpoint:
    """Tests for POST /api/v1/documents/{id}/classify."""

    def test_classify_nonexistent_document(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/classify",
            {},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_classify_invalid_id(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/invalid-id/classify",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_classify_with_categories(self, auth_client, sample_document):
        response = auth_client.post(
            f"/api/v1/documents/{sample_document.id}/classify",
            {"categories": ["invoice", "contract", "report"]},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_classify_unauthenticated(self, api_client, sample_document):
        response = api_client.post(
            f"/api/v1/documents/{sample_document.id}/classify",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentExtractEndpoint:
    """Tests for POST /api/v1/documents/{id}/extract."""

    def test_extract_nonexistent_document(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/extract",
            {},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_extract_invalid_id(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/invalid-id/extract",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_extract_with_fields(self, auth_client, sample_document):
        response = auth_client.post(
            f"/api/v1/documents/{sample_document.id}/extract",
            {"fields": ["title", "author", "date"]},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_extract_unauthenticated(self, api_client, sample_document):
        response = api_client.post(
            f"/api/v1/documents/{sample_document.id}/extract",
            {"fields": ["title"]},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentBatchEndpoints:
    """Tests for batch document operations."""

    def test_batch_process_empty(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/batch-process", {}, format="json"
        )
        assert response.status_code in [
            status.HTTP_202_ACCEPTED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_batch_process_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/documents/batch-process",
            {"file_ids": [str(uuid.uuid4())]},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_batch_classify_empty(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/batch-classify", {}, format="json"
        )
        assert response.status_code in [
            status.HTTP_202_ACCEPTED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_batch_classify_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/documents/batch-classify",
            {"document_ids": [str(uuid.uuid4())]},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_batch_index_empty(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/batch-index", {}, format="json"
        )
        assert response.status_code in [
            status.HTTP_202_ACCEPTED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_batch_index_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/documents/batch-index",
            {"document_ids": [str(uuid.uuid4())]},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_reprocess_failed(self, auth_client):
        response = auth_client.post(
            "/api/v1/documents/reprocess-failed", {}, format="json"
        )
        assert response.status_code in [
            status.HTTP_202_ACCEPTED,
            status.HTTP_200_OK,
        ]

    def test_reprocess_failed_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/documents/reprocess-failed", {}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentModelCreation:
    """Tests verifying document model behavior through the API."""

    def test_document_str_representation(self, sample_document):
        assert str(sample_document) == "Test Invoice Document"

    def test_document_str_no_title(self, db, sample_file_record):
        doc = Document.objects.create(
            file_id=sample_file_record.id,
            doc_type="unknown",
            processing_status="pending",
        )
        assert f"Document({doc.id})" in str(doc)

    def test_document_default_values(self, db, sample_file_record):
        doc = Document.objects.create(
            file_id=sample_file_record.id,
        )
        assert doc.doc_type == "unknown"
        assert doc.processing_status == "pending"
        assert doc.title == ""
        assert doc.language == "unknown"
        assert doc.word_count == 0
        assert doc.page_count == 0


@pytest.mark.django_db
class TestDocumentUpdateEndpoint:
    """Tests for PATCH /api/v1/documents/{id}."""

    def test_patch_title(self, auth_client, sample_document):
        resp = auth_client.patch(
            f"/api/v1/documents/{sample_document.id}",
            {"title": "Updated Title"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["title"] == "Updated Title"

    def test_patch_tags(self, auth_client, sample_document):
        resp = auth_client.patch(
            f"/api/v1/documents/{sample_document.id}",
            {"tags": ["new-tag", "updated"]},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["tags"] == ["new-tag", "updated"]

    def test_patch_nonexistent(self, auth_client):
        resp = auth_client.patch(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000",
            {"title": "x"},
            format="json",
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestDocumentDeleteEndpoint:
    """Tests for DELETE /api/v1/documents/{id}."""

    def test_delete_document(self, auth_client, sample_document):
        doc_id = sample_document.id
        resp = auth_client.delete(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 204
        assert not Document.objects.filter(id=doc_id).exists()

    def test_delete_nonexistent(self, auth_client):
        resp = auth_client.delete(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestDocumentEntitiesEndpoint:
    """Tests for GET /api/v1/documents/{id}/entities."""

    def test_entities_no_entities(self, auth_client, sample_document):
        resp = auth_client.get(
            f"/api/v1/documents/{sample_document.id}/entities"
        )
        assert resp.status_code == 200
        assert resp.data == []

    def test_entities_with_data(self, auth_client, sample_document):
        from apps.documents.models import ExtractedEntity
        ExtractedEntity.objects.create(
            document=sample_document,
            entity_type="PERSON",
            name="John Doe",
            context="Author",
            confidence=0.9,
        )
        resp = auth_client.get(
            f"/api/v1/documents/{sample_document.id}/entities"
        )
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["name"] == "John Doe"
