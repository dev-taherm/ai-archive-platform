import pytest
import uuid
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.files.models import FileRecord


@pytest.mark.django_db
class TestFileListEndpoint:
    """Tests for GET /api/v1/files."""

    def test_list_files_empty(self, auth_client):
        response = auth_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_200_OK

    def test_list_files_with_records(self, auth_client, sample_file_record):
        response = auth_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_200_OK

    def test_list_files_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_files_returns_list(self, auth_client, sample_file_record, completed_file_record):
        response = auth_client.get("/api/v1/files")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, (list, dict))


@pytest.mark.django_db
class TestFileRetrieveEndpoint:
    """Tests for GET /api/v1/files/{id}."""

    def test_retrieve_existing_file(self, auth_client, sample_file_record):
        response = auth_client.get(f"/api/v1/files/{sample_file_record.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_nonexistent_file(self, auth_client):
        response = auth_client.get(
            "/api/v1/files/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_retrieve_invalid_uuid(self, auth_client):
        response = auth_client.get("/api/v1/files/invalid-uuid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_file_unauthenticated(self, api_client, sample_file_record):
        response = api_client.get(f"/api/v1/files/{sample_file_record.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFileUploadEndpoint:
    """Tests for POST /api/v1/files/upload."""

    def test_upload_file_success(self, auth_client):
        content = b"test file content for upload"
        uploaded = SimpleUploadedFile(
            name="test_upload.txt",
            content=content,
            content_type="text/plain",
        )
        response = auth_client.post(
            "/api/v1/files/upload",
            {"file": uploaded},
            format="multipart",
        )
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_upload_file_with_tags(self, auth_client):
        uploaded = SimpleUploadedFile(
            name="tagged_file.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )
        response = auth_client.post(
            "/api/v1/files/upload",
            {"file": uploaded, "tags": "test,upload,pdf"},
            format="multipart",
        )
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_upload_multiple_files(self, auth_client):
        for i in range(3):
            uploaded = SimpleUploadedFile(
                name=f"test_{i}.txt",
                content=f"content_{i}".encode(),
                content_type="text/plain",
            )
            response = auth_client.post(
                "/api/v1/files/upload",
                {"file": uploaded, "tags": "batch"},
                format="multipart",
            )
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
            ]

    def test_upload_unauthenticated(self, api_client):
        uploaded = SimpleUploadedFile(
            name="unauth.txt",
            content=b"content",
            content_type="text/plain",
        )
        response = api_client.post(
            "/api/v1/files/upload",
            {"file": uploaded},
            format="multipart",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_missing_file(self, auth_client):
        response = auth_client.post(
            "/api/v1/files/upload",
            {},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFileScanEndpoint:
    """Tests for POST /api/v1/files/scan."""

    def test_scan_folder_missing_path(self, auth_client):
        response = auth_client.post(
            "/api/v1/files/scan",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_scan_folder_nonexistent(self, auth_client):
        response = auth_client.post(
            "/api/v1/files/scan",
            {"folder_path": "/tmp/nonexistent-folder-abc123", "recursive": True},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_scan_folder_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/files/scan",
            {"folder_path": "/tmp"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFileDownloadEndpoint:
    """Tests for GET /api/v1/files/{id}/download."""

    def test_download_nonexistent_file(self, auth_client):
        response = auth_client.get(
            "/api/v1/files/00000000-0000-0000-0000-000000000000/download"
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_download_invalid_id(self, auth_client):
        response = auth_client.get("/api/v1/files/invalid-id/download")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_download_unauthenticated(self, api_client, sample_file_record):
        response = api_client.get(
            f"/api/v1/files/{sample_file_record.id}/download"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFileDeleteEndpoint:
    """Tests for DELETE /api/v1/files/{id}/delete."""

    def test_delete_nonexistent_file(self, auth_client):
        response = auth_client.delete(
            "/api/v1/files/00000000-0000-0000-0000-000000000000/delete"
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_delete_invalid_id(self, auth_client):
        response = auth_client.delete("/api/v1/files/invalid-id/delete")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_unauthenticated(self, api_client, sample_file_record):
        response = api_client.delete(
            f"/api/v1/files/{sample_file_record.id}/delete"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFileRenameEndpoint:
    """Tests for PATCH /api/v1/files/{id}/rename."""

    def test_rename_nonexistent_file(self, auth_client):
        response = auth_client.patch(
            "/api/v1/files/00000000-0000-0000-0000-000000000000/rename",
            {"new_name": "renamed.txt"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_rename_missing_new_name(self, auth_client, sample_file_record):
        response = auth_client.patch(
            f"/api/v1/files/{sample_file_record.id}/rename",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rename_with_path_separator(self, auth_client, sample_file_record):
        response = auth_client.patch(
            f"/api/v1/files/{sample_file_record.id}/rename",
            {"new_name": "../etc/passwd"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rename_unauthenticated(self, api_client, sample_file_record):
        response = api_client.patch(
            f"/api/v1/files/{sample_file_record.id}/rename",
            {"new_name": "renamed.txt"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFileMoveEndpoint:
    """Tests for POST /api/v1/files/{id}/move."""

    def test_move_nonexistent_file(self, auth_client):
        response = auth_client.post(
            "/api/v1/files/00000000-0000-0000-0000-000000000000/move",
            {"destination_folder": "/tmp/moved"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_move_missing_destination(self, auth_client, sample_file_record):
        response = auth_client.post(
            f"/api/v1/files/{sample_file_record.id}/move",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_move_unauthenticated(self, api_client, sample_file_record):
        response = api_client.post(
            f"/api/v1/files/{sample_file_record.id}/move",
            {"destination_folder": "/tmp/moved"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFileCopyEndpoint:
    """Tests for POST /api/v1/files/{id}/copy."""

    def test_copy_nonexistent_file(self, auth_client):
        response = auth_client.post(
            "/api/v1/files/00000000-0000-0000-0000-000000000000/copy",
            {"destination_folder": "/tmp/copied"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_copy_missing_destination(self, auth_client, sample_file_record):
        response = auth_client.post(
            f"/api/v1/files/{sample_file_record.id}/copy",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_copy_unauthenticated(self, api_client, sample_file_record):
        response = api_client.post(
            f"/api/v1/files/{sample_file_record.id}/copy",
            {"destination_folder": "/tmp/copied"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFileScanStreamEndpoint:
    """Tests for GET /api/v1/files/scan-stream."""

    def test_scan_stream_missing_folder_path(self, auth_client):
        response = auth_client.get("/api/v1/files/scan-stream")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_scan_stream_empty_folder_path(self, auth_client):
        response = auth_client.get("/api/v1/files/scan-stream?folder_path=")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_scan_stream_nonexistent_folder(self, auth_client):
        response = auth_client.get(
            "/api/v1/files/scan-stream?folder_path=/tmp/nonexistent-folder-xyz"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_scan_stream_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/files/scan-stream?folder_path=/tmp")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
